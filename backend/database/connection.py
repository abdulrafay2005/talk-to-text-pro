"""
connection.py
Handles the connection to MongoDB Atlas.

We connect once and keep the connection, so we do not
open a new connection on every request.
Robustness:
    - If the user's OS DNS resolver cannot handle `mongodb+srv://`
      SRV records (a common Windows/network DNS problem), we resolve
      the SRV records ourselves with `dnspython` (which can fall back to
      public resolvers) and build a plain `mongodb://` URI with the
      resolved host list. This keeps the application working even when
      the OS resolver is unreliable.
    - Credentials are read from MONGO_URI and passed through unchanged.
    - We never print, log, or expose the credentials.
"""

import os
import re

from dotenv import load_dotenv

# Load the .env file using an ABSOLUTE path based on this module's location.
# This works regardless of the working directory the app is started from.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "talktotext")

# Connection timeouts (in milliseconds).
SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "15000"))
CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "10000"))
SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "60000"))

_client = None
_database = None


# ============================================================
# SRV resolution helpers
# ============================================================

_SRV_RECORD = re.compile(r"^mongodb\+srv://")


def _resolve_atlas_uri(uri):
    """
    Try to resolve the SRV records for a `mongodb+srv://` URI using
    `dnspython`. If resolution succeeds, return a plain `mongodb://`
    URI with the resolved host list + the exact same query parameters.

    The user/password portion of the URI is preserved verbatim and is
    never printed.

    Returns the original URI when:
        - it is not an SRV URI, or
        - SRV resolution is not needed / not possible.
    """
    if not uri or not _SRV_RECORD.match(uri):
        return uri

    # Split out the credentials + host + (no database) + options.
    # Pattern: mongodb+srv://[user:pass@]host[/db][?options]
    match = re.match(
        r"^mongodb\+srv://(?P<creds>([^/@]+)@)?"
        r"(?P<host>[^/?#]+)"
        r"(?P<rest>.*)$",
        uri,
    )
    if not match:
        return uri

    creds = match.group("creds") or ""
    host = match.group("host")
    rest = match.group("rest") or ""

    # host may include a port (rare for SRV but let's handle it).
    host = host.split(":")[0]

    try:
        import dns.resolver

        answers = dns.resolver.resolve(
            f"_mongodb._tcp.{host}", "SRV", lifetime=10
        )
        servers = []
        for rdata in answers:
            target = str(rdata.target).rstrip(".")
            servers.append(f"{target}:{rdata.port}")

        if not servers:
            return uri

        hosts_list = ",".join(servers)

        # Keep any query parameters from the original URI (e.g. authSource,
        # retryWrites, tls, etc.). If none are present, add tls=true because
        # Atlas always requires TLS but a plain mongodb:// URI does not
        # enable it by default.
        if "?" in rest:
            options = rest.split("?", 1)[1]
            query = f"?{options}"
        else:
            query = "?tls=true"

        resolved = f"mongodb://{creds}{hosts_list}/{query}"
        return resolved

    except Exception:
        # If SRV resolution fails here, let PyMongo handle (and report)
        # the original error. We don't swallow real connectivity failures.
        return uri


def _build_client():
    """
    Create the PyMongo client.

    Uses the original MONGO_URI when it works; otherwise falls back to a
    manual SRV-resolved plain URI so the app keeps working even when the
    OS DNS resolver cannot answer SRV queries.

    Retries a bounded number of times because Atlas connections can be
    transiently dropped on flaky networks (DNS timeouts, TLS resets).
    """
    import time

    from pymongo import MongoClient

    uri = _resolve_atlas_uri(MONGO_URI)

    # Common kwargs for a resilient client.
    common_kwargs = {
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
        "connectTimeoutMS": CONNECT_TIMEOUT_MS,
    }

    max_attempts = int(os.getenv("MONGO_MAX_RETRIES", "4"))
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            client = MongoClient(uri, **common_kwargs)
            # Force a server selection so a broken connection fails fast here
            # with a clear message instead of on the first real request.
            client.admin.command("ping")
            return client
        except Exception as e:
            last_error = e
            print(
                f"[MONGODB] Connection attempt {attempt}/{max_attempts} "
                f"failed: {type(e).__name__}: {str(e)[:200]}"
            )
            if attempt < max_attempts:
                time.sleep(1.5 * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError("MongoDB connection failed after retries.")


def get_database():
    """
    Return the MongoDB database object.
    Connects on the first call and reuses the connection afterwards.
    """
    global _client, _database

    if _database is None:
        if not MONGO_URI:
            raise ValueError(
                "MONGO_URI is missing. Check your .env file."
            )

        _client = _build_client()
        _database = _client[DATABASE_NAME]

    return _database


def get_meetings_collection():
    """
    Shortcut method that returns the "meetings" collection.
    """
    return get_database()["meetings"]


def get_users_collection():
    """
    Shortcut method that returns the "users" collection.
    Passwords are always stored as password hashes (never plain text).
    """
    return get_database()["users"]


def ping():
    """
    Return True if MongoDB is reachable, False otherwise.
    Useful for the health endpoint.
    """
    try:
        db = get_database()
        return db.command("ping").get("ok") == 1.0
    except Exception as e:
        print(f"[MONGODB] Ping failed: {type(e).__name__}: {e}")
        return False
