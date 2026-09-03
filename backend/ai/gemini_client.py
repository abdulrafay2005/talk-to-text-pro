"""
gemini_client.py

A single, shared, robust Gemini client used by both transcription and
summarization.

WHY THIS MODULE EXISTS
======================
The Google GenAI SDK retries HTTP *status* errors (429, 500, 502, 503, 504)
automatically, but it does NOT retry transport-level TLS / connection
errors such as:

    [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
    ConnectError / ConnectionResetError / TimeoutError

These can happen on flaky Wi-Fi or when a network middle-box drops the TLS
handshake. When they happen, the SDK raises immediately. The most reliable
remedy is to create a BRAND NEW client (fresh socket + TLS session) and try
again a bounded number of times.

This module provides:

  * get_client()          -> the shared, reusable client (created once)
  * reset_client()        -> drop the current client so the next call makes a
                             fresh connection (used before a retry)
  * is_retryable_error()  -> decide whether an exception is worth retrying
  * request_with_retry()  -> run any Gemini call with bounded, jittered retries
                             and client-recreation, and NOT retry permanent
                             errors (bad key, bad model, etc.)

It never prints, logs, or exposes the API key.
"""

import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env from an absolute path so it works from any working directory.
# This module lives in backend/ai/, so two dirname() steps -> backend/.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")


# ============================================================
# CLIENT SETTINGS
# ============================================================

# Overall number of attempts (1 original + N retries).
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))

# A generous timeout so audio transcription / long analysis can finish.
# This value is well above the slowest legitimate request.
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "300"))

# Base delay (seconds) before the first retry; doubled on each retry.
RETRY_BASE_DELAY = 2.0
# Maximum single backoff delay to cap the wait time.
RETRY_MAX_DELAY = 30.0


# ============================================================
# SHARED CLIENT
# ============================================================

_client = None


def _create_client():
    """
    Build a brand-new Gemini client with explicit HTTP options:

      * a generous timeout (audio requests can take a while), and
      * the SDK's native retry for HTTP status codes (429/500/502/503/504).

    The native HTTP retry runs *inside* each request attempt; our own retry
    in request_with_retry() handles the transport-level TLS/connection errors
    that the SDK does NOT retry.
    """
    return genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            # HttpOptions.timeout is in MILLISECONDS (the SDK divides by 1000
            # before setting the X-Server-Timeout header). We configure it in
            # seconds and multiply by 1000 here.
            timeout=GEMINI_TIMEOUT_SECONDS * 1000,
            retry_options=types.HttpRetryOptions(
                attempts=4,
                initial_delay=1.5,
                max_delay=20.0,
                exp_base=2.0,
                jitter=0.2,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            ),
        ),
    )


def get_client():
    """
    Return the shared Gemini client, creating it on the first call.
    Reuses the same client for every normal request.
    """
    global _client

    if _client is None:
        _client = _create_client()

    return _client


def reset_client():
    """
    Drop the current client so the next get_client() call makes a
    fresh connection. Used before retrying a transport/TLS failure.
    """
    global _client

    _client = None


# ============================================================
# RETRYABLE ERROR CHECKING
# ============================================================

# Exception classes/types that are ALWAYS transport-level problems worth
# retrying (network blip, dropped TLS handshake, socket timeout). We check
# the exception CLASS/NAME first, then fall back to message text.
_RETRYABLE_EXCEPTION_NAMES = (
    "ConnectTimeout",
    "ReadTimeout",
    "WriteTimeout",
    "TimeoutError",
    "ConnectError",
    "RemoteDisconnected",
    "RemoteProtocolError",
    "ProtocolError",
    "LocalProtocolError",
    "ConnectionError",
    "ConnectionResetError",
    "ConnectionAbortedError",
    "BrokenPipeError",
    "SSLError",
    "ssl.SSLError",
    "socket.timeout",
    "httpcore.ConnectTimeout",
    "httpcore.ReadTimeout",
    "httpcore.ReadError",
    "httpcore.ConnectError",
    "httpx.ConnectTimeout",
    "httpx.ReadTimeout",
    "httpx.WriteTimeout",
    "httpx.ConnectError",
    "httpx.TimeoutException",
    "httpx.ProtocolError",
    "httpx.RemoteProtocolError",
    "NewConnectionError",
    "MaxRetryError",
    "gaierror",
    "aiosqlite.OperationalError",
)

# Substring markers (fallback) that indicate a TEMPORARY problem worth
# retrying (network blip, TLS drop, server overload, rate limit).
_RETRYABLE_TOKENS = (
    "EOF occurred in violation of protocol",
    "UNEXPECTED_EOF",
    "unexpected eof",
    "SSL:",
    "ssl error",
    "tls",
    "Connection reset",
    "Connection aborted",
    "Connection reset by peer",
    "ConnectionError",
    "ConnectError",
    "RemoteDisconnected",
    "Temporary failure in name resolution",
    "name or service not known",
    "getaddrinfo failed",
    "timed out",
    "timeout",
    "socket.timeout",
    "ReadTimeout",
    "WriteTimeout",
    "ConnectTimeout",
    "handshake operation timed out",
    "UNAVAILABLE",
    "RESOURCE_EXHAUSTED",
    "high demand",
    "Internal Server Error",
    "Service Unavailable",
    "Bad Gateway",
    "Too Many Requests",
)

# Server-side HTTP status codes (from ClientError.status_code) that are
# TEMPORARY and worth retrying.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Message tokens that always mean PERMANENT (never retry).
_PERMANENT_TOKENS = (
    "api key not valid",
    "invalid api key",
    "apikey not valid",
    "API key",
    "invalid_api_key",
    "API_KEYS_NOT_ALLOWED",
    "Invalid model",
    "model not found",
    "not found for model",
    "Permission denied",
    "permission denied",
    "billing",
    "invalid argument",
    "malformed",
    "unsupported media",
    "bad request",
    "field_required",
    "unsupported field",
)


def _status_code_of(error):
    """
    Best-effort extraction of an HTTP status code from a Google GenAI
    ClientError (which exposes .status_code / .code) or from any error
    carrying a .status_code attribute.
    """
    for attr in ("status_code", "code", "status"):
        code = getattr(error, attr, None)
        if isinstance(code, int):
            return code
    return None


def is_retryable_error(error):
    """
    Return True for TRANSIENT TLS / connection / timeout / server-overload
    errors that should be retried with a fresh client.

    Return False (never retry) for PERMANENT errors such as:
      * HTTP 400 / INVALID_ARGUMENT (e.g. ''deadline too short'')
      * HTTP 401 / 403 (invalid API key / permissions)
      * invalid model names
      * malformed / unsupported request parameters
    """
    # 1) Explicit HTTP status codes first.
    #    The server returning 429/5xx is retryable; 400/401/403 are not --
    #    even when the message text happens to mention a timeout or TLS.
    code = _status_code_of(error)
    if code is not None:
        if code in _RETRYABLE_STATUS_CODES:
            return True
        if 400 <= code < 500:
            # 4xx are permanent EXCEPT the retryable codes handled above.
            return False
        if 500 <= code < 600:
            return True
        # Other codes: fall through to class/message checks.

    # 2) Explicitly retryable exception classes (transport/TLS/timeout).
    name = type(error).__name__
    for cls_name in _RETRYABLE_EXCEPTION_NAMES:
        if name == cls_name or name.endswith(cls_name):
            return True

    # 3) Permanent markers in the message (never retry).
    message = str(error)
    for token in _PERMANENT_TOKENS:
        if token in message:
            return False

    # 4) Retryable markers in the message (fallback).
    for token in _RETRYABLE_TOKENS:
        if token.lower() in message:
            return True

    return False


def sleep_before_retry(attempt):
    """
    Exponential backoff with jitter so multiple retries do not hit the
    server at the same instant. attempt is 1-based (delay grows each time).
    """
    delay = min(
        RETRY_BASE_DELAY * (2 ** (attempt - 1)),
        RETRY_MAX_DELAY,
    )
    # +/- 20% jitter.
    delay *= random.uniform(0.8, 1.2)
    time.sleep(delay)


# ============================================================
# GENERIC RETRY WRAPPER
# ============================================================

def request_with_retry(
    request_fn,
    *,
    description="Gemini request",
    max_retries=None,
):
    """
    Run any Gemini call with bounded, jittered retries.

    request_fn:
        A zero-argument callable that performs ONE Gemini request and returns
        its result. It MUST build the request using get_client() each time so
        that a recreated client is used after a transport error.

    Behavior:
        Attempt 1 uses the existing (possibly stale) client.
        On a transport/TLS error we reset the client (fresh connection) and
        retry with exponential backoff + jitter.
        Permanent errors (bad key/model/request) fail immediately.
        Returns on the first success, otherwise raises the last error.

    If max_retries is None, GEMINI_MAX_RETRIES is used.
    """
    if max_retries is None:
        max_retries = GEMINI_MAX_RETRIES

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = request_fn()
            print(
                f"[GEMINI] {description}: success on attempt "
                f"{attempt}/{max_retries}."
            )
            return result

        except Exception as e:
            last_error = e
            retryable = is_retryable_error(e)

            print(
                f"[GEMINI] {description}: attempt {attempt}/{max_retries} "
                f"failed ({type(e).__name__}: {e}) retryable={retryable}"
            )

            if not retryable:
                # Permanent error (bad key / model / request): do not retry.
                raise

            if attempt >= max_retries:
                break

            # Create a fresh client (new socket + TLS session) before retrying.
            reset_client()
            sleep_before_retry(attempt)

    # All attempts failed on a retryable error.
    if last_error is not None:
        raise last_error

    raise RuntimeError(
        f"{description} failed after {max_retries} attempts."
    )
