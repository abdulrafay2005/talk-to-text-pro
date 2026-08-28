"""
user.py
Helper functions to build and format user documents
before they are saved to or read from MongoDB.

Only the password hash is stored - never the plain text password.
"""

from datetime import datetime


def create_user_document(name, email, password_hash):
    """
    Build the full user dictionary that gets saved in MongoDB.
    """
    return {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
    }


def convert_user_to_view(user):
    """
    Convert a MongoDB user document into a safe dictionary for the
    frontend. The password hash is never returned to the browser.
    """
    created_at = user.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "created_at": created_at,
    }