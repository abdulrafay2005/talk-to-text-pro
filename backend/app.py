"""
Talk To Text Pro - Backend
This is the entry point of the Flask server.

Run it with:  python app.py
"""

import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from dotenv import load_dotenv

from routes.auth_routes import auth_bp
from routes.meeting_routes import meeting_bp
from routes.pdf_generator import pdf_bp

load_dotenv()


def create_app():
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)

    # Used to sign session cookies securely.
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-this-in-production")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )

    # Hard upload ceiling enforced by Flask itself (in addition to the
    # per-file check in file_utils). Default 250 MB, configurable via env.
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "250"))
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024

    # Return JSON (never HTML) when a request body is too large.
    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        return jsonify({
            "success": False,
            "error": f"The uploaded file is too large. Maximum is {max_upload_mb} MB.",
        }), 413

    # Allow the React frontend (running on a different port) to call our API.
    # supports_credentials lets the browser keep the session cookie.
    CORS(app, supports_credentials=True)

    # Create these folders automatically if they do not exist yet.
    os.makedirs(os.path.join(os.path.dirname(__file__), "uploads"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "generated_pdfs"), exist_ok=True)

    # Register the API routes (blueprints).
    app.register_blueprint(auth_bp)
    app.register_blueprint(meeting_bp)
    app.register_blueprint(pdf_bp)

    # A simple home route so we know the server is alive.
    @app.route("/")
    def home():
        return jsonify({"message": "Talk To Text Pro API is running."})

    return app


if __name__ == "__main__":
    app = create_app()
    # Debug mode is OFF by default; enable it only with FLASK_DEBUG=1
    # so stack traces are never exposed accidentally.
    debug_enabled = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_enabled)