"""
transcription.py

Converts an uploaded audio/video file into plain text.

Uses Gemini Cloud Transcription through the Google GenAI Interactions API.

Pipeline:
    upload media
    -> wait until active
    -> Gemini transcription
    -> cleanup
"""

import os
import re
import time

from dotenv import load_dotenv
from google.genai import types

from ai.gemini_client import (
    get_client,
    reset_client,
    request_with_retry,
)


# ============================================================
# ENVIRONMENT
# ============================================================

# Load .env from an absolute path so it works from any working directory.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH)

GEMINI_TRANSCRIPTION_MODEL = os.getenv(
    "GEMINI_TRANSCRIPTION_MODEL",
    "gemini-3.5-transcribe"
)


# ============================================================
# FFMPEG
# ============================================================

_FFMPEG = "ffmpeg"


# ============================================================
# MEDIA HELPERS
# ============================================================

def _media_has_video(file_path):
    """
    Check whether the media file contains a video stream.

    Returns False if probing fails.
    """

    try:
        import av

        with av.open(file_path) as container:
            return any(
                stream.type == "video"
                for stream in container.streams
            )

    except Exception:
        return False


def _media_duration(file_path):
    """
    Get media duration in seconds using PyAV.

    Returns 0.0 if duration cannot be detected.
    """

    try:
        import av

        with av.open(file_path) as container:

            duration = float(
                container.duration or 0
            ) / 1_000_000

            if duration <= 0:
                return 0.0

            return round(duration, 2)

    except Exception:
        return 0.0


def _mp3_mime_type(file_path):
    """
    Return the correct MIME type for Gemini.
    """

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".mp3":
        return "audio/mpeg"

    if extension == ".wav":
        return "audio/wav"

    if extension == ".mp4":
        return "audio/mp4"

    return "application/octet-stream"


# ============================================================
# FFMPEG AUDIO EXTRACTION
# ============================================================

def _extract_audio_ffmpeg(video_path, output_path):
    """
    Extract only the audio track from a real video.

    The extracted audio is saved as MP3.
    """

    import shutil
    import subprocess

    if shutil.which(_FFMPEG) is None:
        raise RuntimeError(
            "FFmpeg is not installed or not available on PATH. "
            "Real video transcription requires FFmpeg."
        )

    command = [
        _FFMPEG,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "2",
        output_path,
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
        )

    except subprocess.TimeoutExpired as exc:

        raise RuntimeError(
            "FFmpeg timed out while extracting the audio track."
        ) from exc

    if result.returncode != 0:

        detail = (
            result.stderr
            or result.stdout
            or ""
        ).strip()

        raise RuntimeError(
            "FFmpeg failed to extract audio from the video: "
            f"{detail or 'unknown error'}"
        )

    if not os.path.exists(output_path):

        raise RuntimeError(
            "FFmpeg reported success but produced no audio file."
        )


# ============================================================
# WAIT FOR GEMINI FILE
# ============================================================

def _wait_until_active(
    client,
    file_name,
    timeout=120,
    interval=2
):
    """
    Wait until an uploaded Gemini file becomes ACTIVE.

    Raises an error if Gemini reports FAILED
    or if the timeout is reached.

    Temporary network errors during each poll (files.get) are retried a
    bounded number of times so one SSL/connection blip does not fail the
    whole wait. The overall timeout is still respected.
    """

    elapsed = 0.0

    while elapsed < timeout:

        metadata = None
        last_poll_error = None

        # Poll with a few retries on transient network errors.
        for poll_attempt in range(1, 4):
            try:
                metadata = client.files.get(
                    name=file_name
                )
                last_poll_error = None
                break
            except Exception as e:
                last_poll_error = e
                print(
                    "[TRANSCRIPTION] files.get attempt "
                    f"{poll_attempt}/3 failed: "
                    f"{type(e).__name__}: {e}"
                )
                time.sleep(interval)

        if metadata is None and last_poll_error is not None:
            # All three polls failed; raise so we do not loop forever.
            raise last_poll_error

        state = str(
            getattr(
                metadata,
                "state",
                ""
            )
        )

        print(
            f"[TRANSCRIPTION] Gemini file state: {state}"
        )

        if "ACTIVE" in state.upper():
            return metadata

        if "FAILED" in state.upper():

            raise RuntimeError(
                "Gemini could not process the uploaded media "
                "(file state FAILED)."
            )

        time.sleep(interval)

        elapsed += interval

    raise RuntimeError(
        "Timed out waiting for Gemini to prepare the media file."
    )


# ============================================================
# GEMINI TRANSCRIPTION
# ============================================================

def _transcribe_audio_media(
    client,
    audio_path
):
    """
    Upload an audio file to Gemini and request transcription.

    Upload happens ONCE. The transcription request itself is retried with a
    fresh client on transient TLS / connection errors, reusing the SAME
    uploaded file (we never re-upload for every transcription retry).
    """

    mime_type = _mp3_mime_type(
        audio_path
    )

    print(
        "[TRANSCRIPTION] Uploading audio to Gemini..."
    )

    uploaded = None

    try:

        # ----------------------------------------------------
        # UPLOAD ONCE (WITH BOUNDED RETRIES)
        # ----------------------------------------------------

        max_attempts = 5

        for attempt in range(
            1,
            max_attempts + 1
        ):

            try:

                print(
                    f"[TRANSCRIPTION] Upload attempt "
                    f"{attempt}/{max_attempts}..."
                )

                uploaded = client.files.upload(
                    file=audio_path,
                    config=types.UploadFileConfig(
                        mime_type=mime_type
                    ),
                )

                print(
                    "[TRANSCRIPTION] Upload successful "
                    f"on attempt {attempt}."
                )

                break

            except Exception as e:

                print(
                    "[TRANSCRIPTION] Upload attempt "
                    f"{attempt} failed: "
                    f"{type(e).__name__}: {e}"
                )

                if attempt == max_attempts:
                    raise

                wait_time = attempt * 3

                print(
                    "[TRANSCRIPTION] Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

        # ----------------------------------------------------
        # WAIT FOR GEMINI TO PROCESS FILE
        # ----------------------------------------------------

        print(
            "[TRANSCRIPTION] Audio uploaded."
        )

        print(
            "[TRANSCRIPTION] Waiting for active state..."
        )

        metadata = _wait_until_active(
            client,
            uploaded.name
        )

        print(
            "[TRANSCRIPTION] Uploaded file: "
            f"name={uploaded.name}, "
            f"mime={uploaded.mime_type}, "
            f"state={uploaded.state}"
        )

        # ----------------------------------------------------
        # SEND TRANSCRIPTION REQUEST (WITH ROBUST RETRIES)
        # ----------------------------------------------------
        #
        # The SDK does NOT retry transport-level TLS/connection errors, so we
        # use request_with_retry(): on a TLS/SSL/connection error it creates a
        # FRESH client (new socket + TLS session) and retries the same request
        # with the same already-uploaded file. Permanent errors (bad key /
        # model) fail immediately.
        # ----------------------------------------------------

        print(
            "[TRANSCRIPTION] Media ready. "
            "Sending transcription request..."
        )

        def _do_transcribe():
            current_client = get_client()

            interaction = current_client.interactions.create(
                model=GEMINI_TRANSCRIPTION_MODEL,

                input=[
                    {
                        "type": "audio",
                        "uri": metadata.uri,
                        "mime_type": metadata.mime_type,
                    }
                ],

                generation_config={
                    "transcription_config": {
                        "mode": {
                            "type": "smart"
                        }
                    }
                },
            )

            candidate = (
                interaction.output_text
                or ""
            ).strip()

            if not candidate:
                raise RuntimeError(
                    "Gemini returned an empty transcription response."
                )

            return candidate

        transcript = request_with_retry(
            _do_transcribe,
            description="transcription",
        )

        print(
            "[TRANSCRIPTION] Transcription response received."
        )

        print(
            "[TRANSCRIPTION] Transcript characters: "
            f"{len(transcript)}"
        )

        return transcript

    finally:

        # ----------------------------------------------------
        # DELETE GEMINI FILE
        # ----------------------------------------------------
        #
        # Cleanup must NEVER replace the original exception. We swallow any
        # deletion error (and log it separately) so a failed transcription
        # keeps its real error through the finally block.
        # ----------------------------------------------------

        if uploaded is not None:

            try:

                print(
                    "[TRANSCRIPTION] Deleting temporary "
                    "Gemini file..."
                )

                get_client().files.delete(
                    name=uploaded.name
                )

                print(
                    "[TRANSCRIPTION] Gemini file deleted."
                )

            except Exception as e:

                print(
                    "[TRANSCRIPTION] Could not delete "
                    f"Gemini temporary file: {e}"
                )


# ============================================================
# MAIN TRANSCRIPTION FUNCTION
# ============================================================

def transcribe_audio(file_path):
    """
    Transcribe an audio/video file using Gemini Cloud Transcription.

    Supported:

        MP3 -> Gemini
        WAV -> Gemini
        MP4 audio-only -> Gemini
        MP4 video -> FFmpeg audio extraction -> Gemini

    Returns:

        {
            "text": "complete transcript",
            "segments": [],
            "language": "unknown",
            "duration": 42.15
        }
    """

    import tempfile

    client = get_client()

    extension = os.path.splitext(
        file_path
    )[1].lower()

    duration = _media_duration(
        file_path
    )

    print(
        f"[TRANSCRIPTION] Input file: {file_path}"
    )

    print(
        f"[TRANSCRIPTION] Detected media type: "
        f"{extension or 'unknown'}"
    )

    # ========================================================
    # MP3 / WAV
    # ========================================================

    if extension in (
        ".mp3",
        ".wav"
    ):

        print(
            "[TRANSCRIPTION] Audio file. "
            "Uploading directly to Gemini."
        )

        transcript = _transcribe_audio_media(
            client,
            file_path
        )

        print(
            "[TRANSCRIPTION] Gemini transcription completed."
        )

        return {
            "text": transcript,
            "segments": [],
            "language": "unknown",
            "duration": duration,
        }

    # ========================================================
    # MP4
    # ========================================================

    if extension == ".mp4":

        # ----------------------------------------------------
        # AUDIO-ONLY MP4
        # ----------------------------------------------------

        if not _media_has_video(file_path):

            print(
                "[TRANSCRIPTION] Audio-only MP4. "
                "Uploading directly to Gemini."
            )

            transcript = _transcribe_audio_media(
                client,
                file_path
            )

            print(
                "[TRANSCRIPTION] Gemini transcription completed."
            )

            return {
                "text": transcript,
                "segments": [],
                "language": "unknown",
                "duration": duration,
            }

        # ----------------------------------------------------
        # REAL VIDEO MP4
        # ----------------------------------------------------

        print(
            "[TRANSCRIPTION] Real video detected. "
            "Extracting audio with FFmpeg..."
        )

        temp_dir = tempfile.mkdtemp(
            prefix="ttt_audio_"
        )

        temp_audio = os.path.join(
            temp_dir,
            "extracted_audio.mp3"
        )

        try:

            _extract_audio_ffmpeg(
                file_path,
                temp_audio
            )

            print(
                "[TRANSCRIPTION] Audio extraction complete."
            )

            transcript = _transcribe_audio_media(
                client,
                temp_audio
            )

            print(
                "[TRANSCRIPTION] Gemini transcription completed."
            )

            return {
                "text": transcript,
                "segments": [],
                "language": "unknown",
                "duration": duration,
            }

        finally:

            try:

                import shutil

                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )

            except Exception:
                pass

            print(
                "[TRANSCRIPTION] Cleaning temporary audio file..."
            )

    # ========================================================
    # UNSUPPORTED FILE
    # ========================================================

    raise RuntimeError(
        f"Unsupported media type '{extension}'. "
        "Supported formats: .mp3, .wav, .mp4"
    )


# ============================================================
# TRANSCRIPT CLEANING
# ============================================================

FILLER_WORDS = [
    "um",
    "uh",
    "uhh",
    "umm",
    "uhm",
    "erm",
    "er",
    "mm",
    "hmm",
    "mmm",
]


SAFE_DOUBLE_WORDS = {
    "okay",
    "yeah",
    "yep",
    "right",
    "well",
    "no",
    "fine",
}


ARTIFACT_PATTERNS = re.compile(
    r"\[(?:music|applause|laughter|laughs|coughing|"
    r"background noise|silence|indistinct|inaudible|pause)\]"
    r"|"
    r"\((?:music|applause|laughter|laughs|coughing|"
    r"background noise|silence|indistinct|inaudible|pause)\)",
    re.IGNORECASE,
)


def clean_transcript(raw_text):
    """
    Clean the transcript for display and AI analysis.

    The original raw transcript is not modified.
    """

    text = raw_text or ""

    # --------------------------------------------------------
    # Remove transcript artifacts
    # --------------------------------------------------------

    text = ARTIFACT_PATTERNS.sub(
        "",
        text
    )

    # --------------------------------------------------------
    # Build filler-word regex
    # --------------------------------------------------------

    filler_inline = "|".join(
        re.escape(word)
        for word in FILLER_WORDS
    )

    # --------------------------------------------------------
    # Remove fillers surrounded by commas
    #
    # "We, like, decided" -> "We decided"  (filler + BOTH commas removed)
    # We replace with a single space (not a comma) so joined words do not
    # merge. Trailing whitespace is cleaned up later.
    # --------------------------------------------------------

    text = re.sub(
        r",\s*(?:" + filler_inline + r")\s*,",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove "you know"
    # --------------------------------------------------------

    text = re.sub(
        r",\s*you\s+know\s*,",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"([.;:])\s*you\s+know\s*,\s*",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^you\s+know\s*,\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove "like"
    # --------------------------------------------------------

    text = re.sub(
        r",\s*like\s*,",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"([.;:])\s*like\s*,",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^like\s*,\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove "basically"
    # --------------------------------------------------------

    text = re.sub(
        r"([.;:])\s*basically\b\s*,?\s*",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bbasically\b\s*,",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^basically\s*,?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove standalone filler words
    # --------------------------------------------------------

    for filler in FILLER_WORDS:

        text = re.sub(
            r"\b" + re.escape(filler) + r"\b",
            "",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # Remove repeated words
    #
    # Example:
    # "we we we need to talk"
    # -> "we need to talk"
    # --------------------------------------------------------

    text = re.sub(
        r"\b(\w+)(\s+\1){2,}\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove safe double words
    #
    # Example:
    # "okay okay let's start"
    # -> "okay let's start"
    # --------------------------------------------------------

    for word in SAFE_DOUBLE_WORDS:

        text = re.sub(
            r"\b"
            + re.escape(word)
            + r"\b"
            r"(\s+"
            + re.escape(word)
            + r"\b)",
            word,
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # Remove consecutive duplicate sentences
    # --------------------------------------------------------

    text = _remove_duplicate_sentences(
        text
    )

    # --------------------------------------------------------
    # Clean punctuation
    # --------------------------------------------------------

    text = re.sub(
        r",\s*,",
        ",",
        text
    )

    text = re.sub(
        r"\.\s*\.",
        ".",
        text
    )

    text = re.sub(
        r"\s+([,.;:?!])",
        r"\1",
        text
    )

    text = re.sub(
        r"^[\s,.;:?!]+",
        "",
        text
    )

    text = re.sub(
        r"\s{2,}",
        " ",
        text
    )

    return text.strip()


def _remove_duplicate_sentences(text):
    """
    Remove an exact consecutive duplicate sentence.
    """

    pieces = re.split(
        r"(?<=[.!?])\s+",
        text.strip()
    )

    kept = []

    previous = None

    for piece in pieces:

        current = piece.strip()

        if (
            current
            and previous is not None
            and current.lower() == previous.lower()
        ):
            continue

        kept.append(
            current
        )

        previous = current

    return " ".join(
        piece
        for piece in kept
        if piece
    )