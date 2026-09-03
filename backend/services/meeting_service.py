"""
meeting_service.py
This file connects all the steps of the pipeline together:

    upload -> transcribe -> clean -> (optional) translate -> AI analysis -> save in MongoDB
"""

import os
import time

from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load .env from an absolute path so it works from any working directory.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH)

from ai.summarization import analyze_meeting, answer_question
from ai.transcription import clean_transcript, transcribe_audio
from ai.translation import translate_text
from database.connection import get_meetings_collection
from models.meeting import convert_meeting_to_view, create_meeting_document, string_to_object_id
from utils.sharing import generate_share_token, is_valid_share_token
from utils.file_utils import save_uploaded_file, validate_uploaded_file
from utils.token_utils import build_optimization_stats, optimized_text_for

# The uploads folder lives inside the backend folder.
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

# Same per-chunk token budget used by the AI analysis (summarization.py).
# Compression + chunking only ever happen above this limit.
MAX_ANALYSIS_TOKENS = int(os.getenv("MAX_ANALYSIS_TOKENS", "1000"))


def _log(step, message):
    """Print a timestamped pipeline log line."""
    print(f"[PIPELINE] {step}: {message}")


def process_audio_file(file, title, translate_to, user_id):
    """
    Process one uploaded file from start to finish.
    Returns a dictionary with "success" plus either the new meeting or an error.
    """
    pipeline_start = time.time()
    _log("UPLOAD", f"Received file='{file.filename}', title='{title}', translate_to={translate_to}")

    # 1. Validate the file (exists, has a name, allowed extension).
    _log("VALIDATION", "Validating uploaded file...")
    is_valid, error_message, secure_filename = validate_uploaded_file(file)
    if not is_valid:
        _log("VALIDATION", f"FAILED: {error_message}")
        return {"success": False, "error": error_message}
    _log("VALIDATION", f"OK: secure_filename={secure_filename}")

    # 2. Save the file into the uploads folder.
    _log("FILE SAVE", "Saving uploaded file to disk...")
    file_path = save_uploaded_file(file, secure_filename, UPLOAD_FOLDER)
    _log("FILE SAVE", f"Saved to {file_path}")

    try:
        # 3. Transcribe with Gemini Cloud Transcription.
        _log("TRANSCRIPTION START", f"Starting cloud transcription on {file_path}...")
        transcription_start = time.time()
        transcription = transcribe_audio(file_path)
        transcription_elapsed = time.time() - transcription_start
        raw_text = transcription["text"]
        _log("TRANSCRIPTION COMPLETE", f"Done in {transcription_elapsed:.1f}s. Duration={transcription['duration']}s, Chars={len(raw_text)}")

        if not raw_text.strip():
            _log("TRANSCRIPTION COMPLETE", "FAILED: No speech found in file.")
            return {"success": False, "error": "No speech was found in the file."}

        # 4. Clean the transcript (remove filler words, extra spaces).
        _log("CLEANING", "Cleaning transcript...")
        cleaned_text = clean_transcript(raw_text)
        _log("CLEANING", f"Done. Chars: {len(raw_text)} -> {len(cleaned_text)}")

        # 5. Build the text & token optimization statistics.
        _log("TOKEN OPTIMIZATION", "Computing token optimization stats...")
        optimization = build_optimization_stats(cleaned_text, MAX_ANALYSIS_TOKENS)

        optimized_text = optimized_text_for(cleaned_text, MAX_ANALYSIS_TOKENS)
        _log("TOKEN OPTIMIZATION", f"Done. Original tokens={optimization['original_tokens']}, Optimized tokens={optimization['optimized_tokens']}, Applied={optimization['optimization_applied']}")

        # 6. Optional translation.
        translated_text = None
        text_for_ai = cleaned_text
        if translate_to:
            _log("TRANSLATION", f"Translating to '{translate_to}'...")
            translation_start = time.time()
            try:
                translated_text = translate_text(cleaned_text, translate_to)
                text_for_ai = translated_text
                _log("TRANSLATION", f"Done in {time.time() - translation_start:.1f}s. Chars={len(translated_text)}")
            except Exception as e:
                _log("TRANSLATION", f"FAILED ({type(e).__name__}: {e}). Continuing without translation.")
                translated_text = None
        else:
            _log("TRANSLATION", "Skipped (no target language).")

        # 7. AI analysis (returns meeting intelligence JSON).
        _log("GEMINI START", "Sending transcript to Gemini for analysis...")
        gemini_start = time.time()
        analysis = analyze_meeting(text_for_ai)
        gemini_elapsed = time.time() - gemini_start
        _log("GEMINI COMPLETE", f"Done in {gemini_elapsed:.1f}s. Type={analysis.get('meeting_type', '?')}, Sentiment={analysis.get('sentiment', '?')}")

        # 8. Build the meeting document and save it to MongoDB Atlas.
        _log("MONGODB SAVE", "Building meeting document and saving to MongoDB...")
        meeting = create_meeting_document(
            title, transcription, cleaned_text, translated_text, translate_to, analysis,
            user_id, optimization, optimized_text=optimized_text,
        )
        save_start = time.time()
        result = get_meetings_collection().insert_one(meeting)
        meeting["_id"] = result.inserted_id
        _log("MONGODB SAVE", f"Saved in {time.time() - save_start:.1f}s. _id={result.inserted_id}")

        pipeline_elapsed = time.time() - pipeline_start
        _log("PIPELINE COMPLETE", f"Total pipeline took {pipeline_elapsed:.1f}s")

        return {"success": True, "meeting": convert_meeting_to_view(meeting)}

    finally:
        # Always delete the uploaded file after processing to save space.
        if os.path.exists(file_path):
            os.remove(file_path)
            _log("CLEANUP", f"Deleted temp file {file_path}")


def get_all_meetings(user_id):
    """
    Return all meetings belonging to one user, newest first.
    """
    collection = get_meetings_collection()
    meetings = list(collection.find({"user_id": user_id}).sort("created_at", -1))

    for meeting in meetings:    
        meeting["_id"] = str(meeting["_id"])
    return [convert_meeting_to_view(meeting) for meeting in meetings]


def get_meeting_by_id(meeting_id, user_id):
    """
    Return one meeting, but only if it belongs to the given user.
    Returns None if the id is invalid / not found / not owned by the user.
    """
    object_id = string_to_object_id(meeting_id)
    if object_id is None:
        return None

    meeting = get_meetings_collection().find_one({"_id": object_id, "user_id": user_id})
    if meeting is None:
        return None

    return convert_meeting_to_view(meeting)


def delete_meeting(meeting_id, user_id):
    """
    Delete a meeting, but only if it belongs to the given user.
    Returns True if a meeting was deleted.
    """
    object_id = string_to_object_id(meeting_id)
    if object_id is None:
        return False

    result = get_meetings_collection().delete_one({"_id": object_id, "user_id": user_id})
    return result.deleted_count > 0


def update_meeting_translation(meeting_id, target, user_id):
    """
    Translate the cleaned transcript again (after the meeting was saved)
    and store the new translation. Returns the updated meeting or None.
    """
    meeting = get_meeting_by_id(meeting_id, user_id)
    if meeting is None:
        return None

    translated = translate_text(meeting["transcript_cleaned"], target)

    get_meetings_collection().update_one(
        {"_id": ObjectId(meeting_id), "user_id": user_id},
        {"$set": {"translated_transcript": translated, "translate_to": target}},
    )

    return get_meeting_by_id(meeting_id, user_id)


def ask_meeting(meeting_id, question, user_id):
    """
    Answer a user question about a meeting using the real AI.
    Returns the answer text, or None if the meeting does not exist
    (or does not belong to the user).
    """
    meeting = get_meeting_by_id(meeting_id, user_id)
    if meeting is None:
        return None

    return answer_question(meeting, question)


def enable_sharing(meeting_id, user_id):
    """
    Create (or reuse) a random share token for a meeting the user owns.
    Returns (share_token, share_url) or None when not found / not owned.
    """
    object_id = string_to_object_id(meeting_id)
    if object_id is None:
        return None

    owned = get_meetings_collection().find_one(
        {"_id": object_id, "user_id": user_id}
    )
    if owned is None:
        return None

    token = owned.get("share_token")
    if not token or not is_valid_share_token(token):
        token = generate_share_token()
        get_meetings_collection().update_one(
            {"_id": object_id},
            {"$set": {"share_token": token, "share_enabled": True}},
        )

    return token


def get_shared_meeting(token):
    """
    Read-only lookup used by the public share link. Only returns the
    meeting whose random share token matches exactly. Never falls back
    to any other field, so other users' meetings can never be found
    by guessing ids or scanning.
    """
    if not is_valid_share_token(token):
        return None

    meeting = get_meetings_collection().find_one(
        {"share_token": token, "share_enabled": True}
    )
    if meeting is None:
        return None

    return convert_meeting_to_view(meeting)


def disable_sharing(meeting_id, user_id):
    """
    Turn off sharing for a meeting (removes the token). Returns True/False.
    """
    object_id = string_to_object_id(meeting_id)
    if object_id is None:
        return False

    result = get_meetings_collection().update_one(
        {"_id": object_id, "user_id": user_id},
        {"$set": {"share_enabled": False}, "$unset": {"share_token": ""}},
    )
    return result.modified_count > 0