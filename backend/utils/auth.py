"""
auth.py
Small helpers for session-based authentication.

The Flask session is used: after a successful login we store the user id
in the session cookie (signed with SECRET_KEY, HttpOnly). Every protected
route checks it with the login_required decorator.
"""

from functools import wraps

from bson.objectid import ObjectId
from flask import jsonify, session

from database.connection import get_users_collection


def get_current_user():
    """
    Return the logged-in user document, or None if no one is logged in.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    try:
        return get_users_collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def get_current_user_id():
    """
    Return the logged-in user id as a string, or None.
    """
    return session.get("user_id")


def login_required(view_function):
    """
    Decorator that rejects requests from users who are not logged in.
    """
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "You must be logged in to do this."}), 401
        return view_function(*args, **kwargs)

    return wrapped