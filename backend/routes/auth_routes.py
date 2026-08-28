"""
auth_routes.py
Real authentication endpoints backed by MongoDB Atlas.

    POST /api/auth/register   create a new account
    POST /api/auth/login      sign in and start a session
    GET  /api/auth/me         return the logged-in user (or 401)
    POST /api/auth/logout     end the session

Passwords are hashed with Werkzeug (pbkdf2) before being stored.
The plain text password is never kept anywhere.
"""

import re

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database.connection import get_users_collection
from models.user import convert_user_to_view, create_user_document

auth_bp = Blueprint("auth", __name__)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """
    Create a new account and save it in MongoDB.
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name:
        return jsonify({"error": "Please enter your name."}), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 4:
        return jsonify({"error": "Your password must be at least 4 characters."}), 400

    users = get_users_collection()

    if users.find_one({"email": email}):
        return jsonify({"error": "An account with this email already exists."}), 400

    user_document = create_user_document(name, email, generate_password_hash(password))
    result = users.insert_one(user_document)
    user_document["_id"] = result.inserted_id

    return jsonify({"success": True, "user": convert_user_to_view(user_document)}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Sign a user in. On success the user id is stored in the session cookie.
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Please enter your email and password."}), 400

    user = get_users_collection().find_one({"email": email})

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = str(user["_id"])

    return jsonify({"user": convert_user_to_view(user)})


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    """
    Return the currently logged-in user, so the frontend can restore
    the session when the app loads. 401 when nobody is logged in.
    """
    from utils.auth import get_current_user

    user = get_current_user()
    if user is None:
        return jsonify({"error": "You are not logged in."}), 401

    return jsonify({"user": convert_user_to_view(user)})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    End the session.
    """
    session.clear()
    return jsonify({"success": True})