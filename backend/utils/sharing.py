"""
sharing.py
Pure helpers for the meeting share-link feature.

Security model:
    - Each meeting gets a random, unguessable token
      (secrets.token_urlsafe -> high entropy).
    - Public lookup matches ONLY {"share_token": token, "share_enabled": True}.
      No ids, emails or usernames are ever involved, so no other meeting can
      be found by guessing or enumeration.
    - The token lives in the URL (standard for read-only shares) and removes
      the meeting's data when sharing is disabled.
"""

import re
import secrets

# token_urlsafe generates A-Za-z0-9_- (no padding). 22 chars ~ 132 bits.
TOKEN_ALPHABET = re.compile(r"^[A-Za-z0-9_-]+$")
MIN_TOKEN_LENGTH = 20
MAX_TOKEN_LENGTH = 64


def generate_share_token():
    """
    Return a fresh random share token.
    """
    return secrets.token_urlsafe(22)


def is_valid_share_token(token):
    """
    Strictly validate a share token before it is used in a query.
    Prevents any weird input (injection attempts, oversized strings)
    from reaching MongoDB.
    """
    if not isinstance(token, str):
        return False
    if not (MIN_TOKEN_LENGTH <= len(token) <= MAX_TOKEN_LENGTH):
        return False
    return bool(TOKEN_ALPHABET.match(token))


def build_share_url(token, base_url):
    """
    Build the full shareable URL:  <base>/share/<token>
    """
    token = (token or "").strip()
    if not is_valid_share_token(token):
        return None

    base = (base_url or "").rstrip("/")
    return f"{base}/share/{token}"