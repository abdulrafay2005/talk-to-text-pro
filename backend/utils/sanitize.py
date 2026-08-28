"""
sanitize.py
Helpers that clean user-provided text before it is used or stored.

Purpose:
    - never let controlled text break the API, a document, or a filename
    - strip control characters and normalize whitespace
    - enforce reasonable length limits
    - keep the original wording (sanitizing is NOT the same as cleaning
      the transcript: no content is removed here)
"""

import re

# Everything below the printable ASCII range plus DEL are control chars.
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE_RUN = re.compile(r"\s+")


def sanitize_text(value, max_length=120, fallback=""):
    """
    Return a safe, trimmed version of a user-provided string.

    - None/empty stays None/empty (unless a fallback is given)
    - control characters are removed
    - whitespace runs collapse to a single space
    - the string is truncated to max_length characters
    """
    if value is None:
        return fallback if isinstance(fallback, str) else ""

    text = str(value)
    text = CONTROL_CHARACTERS.sub("", text)
    text = WHITESPACE_RUN.sub(" ", text).strip()

    if not text:
        return fallback if isinstance(fallback, str) else ""

    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()

    return text


def sanitize_title(value, max_length=120, fallback="Untitled Meeting"):
    """
    Sanitize a meeting title. Falls back to a default when empty.
    """
    return sanitize_text(value, max_length=max_length, fallback=fallback)


def sanitize_question(value, max_length=500):
    """
    Sanitize a user's question for the "Ask your meeting" endpoint.
    """
    return sanitize_text(value, max_length=max_length, fallback="")