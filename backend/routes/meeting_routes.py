"""
meeting_routes.py
API endpoints for uploading files and managing meetings.

All meeting endpoints require the user to be logged in, and every meeting
is scoped to the logged-in user (ownership is enforced here).

The one intentionally public endpoint is GET /api/shared/<token>, which
returns ONLY the meeting whose unguessable share token matches.
"""

from flask import Blueprint, jsonify, request

from services import meeting_service
from utils.auth import login_required, get_current_user_id
from utils.sanitize import sanitize_question, sanitize_title
from utils.sharing import build_share_url, is_valid_share_token

meeting_bp = Blueprint("meetings", __name__)

# Languages the translation endpoint accepts (matches the frontend list).
ALLOWED_TARGET_LANGUAGES = {"en", "ur", "es", "fr", "ar", "hi", "de"}


@meeting_bp.route("/api/transcribe", methods=["POST"])
@login_required
def transcribe():
    """
    Upload an audio/video file.
    The backend will transcribe it, clean it, (optionally) translate it,
    analyze it, and save the result in MongoDB.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file was sent with the request."}), 400

    file = request.files["file"]

    # Optional form fields from the frontend (sanitized before use).
    title = sanitize_title(request.form.get("title", ""))

    translate_to = request.form.get("translate_to", "").strip()
    if not translate_to:
        translate_to = None
    elif translate_to not in ALLOWED_TARGET_LANGUAGES:
        translate_to = None

    print("[/api/transcribe] REQUEST RECEIVED")
    print("[/api/transcribe] filename:", file.filename)
    print("[/api/transcribe] title:", title)
    print("[/api/transcribe] user_id:", get_current_user_id())
    print("[/api/transcribe] Starting process_audio_file...")

    try:
        result = meeting_service.process_audio_file(
            file,
            title,
            translate_to,
            get_current_user_id()
        )
    except Exception as e:
        # Never let a raw exception surface as an empty 500 response.
        print(f"[TRANSCRIBE ERROR] {type(e).__name__}: {e}")
        return jsonify({
            "success": False,
            "error": "Meeting processing failed. Check the backend terminal for details.",
        }), 500

    print("[/api/transcribe] process_audio_file FINISHED")
    print("[/api/transcribe] result success:", result.get("success"))

    if result.get("success"):
        return jsonify(result), 201

    return jsonify(result), 400


@meeting_bp.route("/api/meetings", methods=["GET"])
@login_required
def list_meetings():
    """
    Return the logged-in user's saved meetings (history), newest first.
    """
    meetings = meeting_service.get_all_meetings(get_current_user_id())
    return jsonify({"meetings": meetings})


@meeting_bp.route("/api/meetings/<meeting_id>", methods=["GET"])
@login_required
def get_meeting(meeting_id):
    """
    Return a single meeting by id (ownership checked).
    """
    meeting = meeting_service.get_meeting_by_id(meeting_id, get_current_user_id())
    if meeting is None:
        return jsonify({"error": "Meeting not found."}), 404

    return jsonify({"meeting": meeting})


@meeting_bp.route("/api/meetings/<meeting_id>", methods=["DELETE"])
@login_required
def delete_meeting(meeting_id):
    """
    Delete a meeting by id (ownership checked).
    """
    deleted = meeting_service.delete_meeting(meeting_id, get_current_user_id())
    if not deleted:
        return jsonify({"error": "Meeting not found."}), 404

    return jsonify({"success": True})


@meeting_bp.route("/api/meetings/<meeting_id>/translate", methods=["POST"])
@login_required
def translate_meeting(meeting_id):
    """
    Translate an already saved meeting's transcript into a target language.
    The body should send JSON like:  {"target": "es"}
    """
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()

    if not target:
        return jsonify({"error": "A target language is required."}), 400

    if target not in ALLOWED_TARGET_LANGUAGES:
        return jsonify({"error": "That target language is not supported."}), 400

    meeting = meeting_service.update_meeting_translation(meeting_id, target, get_current_user_id())
    if meeting is None:
        return jsonify({"error": "Meeting not found."}), 404

    return jsonify({"meeting": meeting})


@meeting_bp.route("/api/meetings/<meeting_id>/ask", methods=["POST"])
@login_required
def ask_meeting(meeting_id):
    """
    Ask a real question about a meeting. The answer comes from Ollama
    and uses ONLY the meeting transcript. Body:  {"question": "..."}
    """
    data = request.get_json(silent=True) or {}
    question = sanitize_question(data.get("question"))

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    answer = meeting_service.ask_meeting(meeting_id, question, get_current_user_id())
    if answer is None:
        return jsonify({"error": "Meeting not found."}), 404

    return jsonify({"answer": answer})


@meeting_bp.route("/api/meetings/<meeting_id>/share", methods=["POST"])
@login_required
def share_meeting(meeting_id):
    """
    Enable sharing for a meeting the user owns.
    Returns the unguessable share token so the frontend can build and
    copy a read-only share link.
    """
    token = meeting_service.enable_sharing(meeting_id, get_current_user_id())
    if token is None:
        return jsonify({"error": "Meeting not found."}), 404

    # base from request host (scheme://host[:port]).
    base_url = request.host_url.rstrip("/")
    share_url = build_share_url(token, base_url)

    return jsonify({"share_token": token, "share_url": share_url})


@meeting_bp.route("/api/meetings/<meeting_id>/share", methods=["DELETE"])
@login_required
def unshare_meeting(meeting_id):
    """
    Disable sharing and remove the share token (ownership checked).
    """
    if not meeting_service.disable_sharing(meeting_id, get_current_user_id()):
        return jsonify({"error": "Meeting not found."}), 404

    return jsonify({"success": True})


@meeting_bp.route("/api/shared/<share_token>", methods=["GET"])
def get_shared(share_token):
    """
    PUBLIC read-only share link. Returns ONLY the meeting whose random
    share token matches exactly (strictly validated first). No login is
    needed - that is the point of sharing - but nothing else can be
    guessed or enumerated: the token is 22 random chars and the query is
    scoped to {"share_token": token, "share_enabled": True}.
    """
    if not is_valid_share_token(share_token):
        return jsonify({"error": "This share link is not valid."}), 404

    meeting = meeting_service.get_shared_meeting(share_token)
    if meeting is None:
        return jsonify({"error": "This shared meeting could not be found or was unshared."}), 404

    return jsonify({"meeting": meeting})