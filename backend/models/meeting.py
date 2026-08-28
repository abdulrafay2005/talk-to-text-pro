"""
meeting.py
Helper functions to build and format meeting documents
before they are saved to or read from MongoDB.
"""

from datetime import datetime

from bson.objectid import ObjectId


def create_meeting_document(title, transcription, cleaned_text,
                            translated_text, translate_to, analysis,
                            user_id, optimization, optimized_text=None):
    """
    Build the full meeting dictionary that gets saved in MongoDB.
    user_id is the id of the account that uploaded the meeting.
    optimization holds the text & token optimization statistics.

    The three transcript versions are stored separately and NEVER
    overwrite each other:
        transcript_raw        -> the original ASR output (verbatim)
        transcript_cleaned    -> conservative filler/artifact cleaning
        transcript_optimized  -> the compressed + chunked text ONLY sent
                                 to the AI analysis (never shown as the
                                 user's transcript)
    """
    return {
        "title": title,
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "original_language": transcription["language"],
        "duration": transcription["duration"],

        # Transcripts (kept as three separate, independent versions)
        "transcript_raw": transcription["text"],
        "transcript_cleaned": cleaned_text,
        "transcript_optimized": optimized_text,
        "translated_transcript": translated_text,
        "translate_to": translate_to,

        # AI analysis
        "meeting_type": analysis["meeting_type"],
        "summary": analysis["summary"],
        "key_points": analysis["key_points"],
        "topics": analysis["topics"],
        "decisions": analysis["decisions"],
        "action_items": analysis["action_items"],
        "unresolved_issues": analysis["unresolved_issues"],
        "sentiment": analysis["sentiment"],

        # Text & token optimization statistics
        "optimization": optimization,
    }


def string_to_object_id(meeting_id):
    """
    Convert a meeting id (string) into a MongoDB ObjectId.
    Returns None if the id is not valid.
    """
    try:
        return ObjectId(meeting_id)
    except Exception:
        return None


def convert_meeting_to_view(meeting):
    """
    Convert a MongoDB document into a dictionary the React
    frontend can easily display.
    """
    meeting["_id"] = str(meeting["_id"])

    if isinstance(meeting.get("created_at"), datetime):
        meeting["created_at"] = meeting["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    return meeting