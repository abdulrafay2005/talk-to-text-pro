"""
transcription.py
Converts an uploaded audio/video file into plain text.

Uses Gemini Cloud Transcription (gemini-3.5-transcribe) through the
Google GenAI Interactions API, which avoids the need to run a heavy local
Whisper model on CPU.

The active pipeline calls transcribe_audio(file_path) which internally:
    upload media -> wait until active -> Gemini transcription -> cleanup
"""

import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Gemini cloud transcription model. Configurable via .env.
GEMINI_TRANSCRIPTION_MODEL = os.getenv(
    "GEMINI_TRANSCRIPTION_MODEL", "gemini-3.5-transcribe"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

_client = None


def _get_client():
    """
    Reuse a single Gemini client for the whole process.
    """
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


_FFMPEG = "ffmpeg"


def _media_has_video(file_path):
    """
    Probe a media file with PyAV and report whether it contains a video stream.
    Returns False when probing fails (safe default: treat as audio-only).
    """
    try:
        import av

        with av.open(file_path) as container:
            return any(
                stream.type == "video" for stream in container.streams
            )
    except Exception:
        return False


def _media_duration(file_path):
    """
    Best-effort duration in seconds using PyAV. Falls back to 0.
    """
    try:
        import av

        with av.open(file_path) as container:
            duration = float(container.duration or 0) / 1_000_000
            if duration <= 0:
                return 0.0
            return round(duration, 2)
    except Exception:
        return 0.0


def _mp3_mime_type(file_path):
    """
    Return the MIME type Gemini should treat an audio file as:

      .mp3 -> audio/mpeg
      .wav -> audio/wav
      .mp4 -> audio/mp4 (audio-only container, extracted or native)
    """
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".mp3":
        return "audio/mpeg"
    if extension == ".wav":
        return "audio/wav"

    return "audio/mp4"


def _extract_audio_ffmpeg(video_path, output_path):
    """
    Extract ONLY the audio track from a real video using the locally
    installed FFmpeg, writing it to `output_path` (.mp3).

    Raises a RuntimeError with a clear message when FFmpeg is unavailable
    or the extraction fails, so the caller never silently hangs.
    """
    import shutil
    import subprocess

    if shutil.which(_FFMPEG) is None:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. "
            "Real video transcription requires FFmpeg to extract its audio track."
        )

    # -y: overwrite, -vn: drop all video, -acodec/libmp3lame: mp3 audio,
    # -q:a 2: high-quality VBR audio.
    command = [
        _FFMPEG,
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
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
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"FFmpeg failed to extract audio from the video: {detail or 'unknown error'}"
        )

    if not os.path.exists(output_path):
        raise RuntimeError(
            "FFmpeg reported success but produced no audio file."
        )


def _wait_until_active(client, file_name, timeout=120, interval=2):
    """
    Poll the uploaded file until it reaches ACTIVE or FAILED state.
    Returns the File metadata once ACTIVE, else raises.
    """
    elapsed = 0.0
    while elapsed < timeout:
        metadata = client.files.get(name=file_name)
        state = str(getattr(metadata, "state", ""))

        if "ACTIVE" in state.upper():
            return metadata
        if "FAILED" in state.upper():
            raise RuntimeError(
                f"Gemini could not process the uploaded media (file state FAILED)."
            )

        time.sleep(interval)
        elapsed += interval

    raise RuntimeError(
        f"Timed out waiting for Gemini to prepare the media file."
    )


def _transcribe_audio_media(client, audio_path):
    """
    Upload a pure-audio file to Gemini and request transcription.

    Returns the raw transcript text. The uploaded Gemini file is always
    deleted before returning.
    """
    mime_type = _mp3_mime_type(audio_path)

    print("[TRANSCRIPTION] Uploading audio to Gemini...")

    uploaded = None
    try:
        uploaded = client.files.upload(
            file=audio_path,
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        print("[TRANSCRIPTION] Audio uploaded. Waiting for active state...")

        metadata = _wait_until_active(client, uploaded.name)
        print("[TRANSCRIPTION] Media ready. Sending transcription request...")

        interaction = client.interactions.create(
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
                    "mode": {"type": "smart"},
                }
            },
        )

        return (interaction.output_text or "").strip()
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                # Best-effort cleanup; never hide the real error.
                pass


def transcribe_audio(file_path):
    """
    Transcribe an audio/video file with Gemini Cloud Transcription.

    Pipeline:
      MP3/WAV           -> uploaded directly to Gemini
      Real video MP4    -> audio track extracted locally with FFmpeg ->
                           extracted audio uploaded to Gemini

    Returns:
        {
            "text": "complete transcript",
            "segments": [],          # no invented timestamps
            "language": "unknown",   # no language tag from the model used
            "duration": 42.15        # from the original media container
        }
    """
    import tempfile

    client = _get_client()
    extension = os.path.splitext(file_path)[1].lower()
    duration = _media_duration(file_path)

    print(f"[TRANSCRIPTION] Input file: {file_path}")
    print(f"[TRANSCRIPTION] Detected media type: {extension or 'unknown'}")

    # Audio files go straight to Gemini; no video stream is involved.
    if extension in (".mp3", ".wav"):
        print(f"[TRANSCRIPTION] Audio file. Uploading directly to Gemini.")
        transcript = _transcribe_audio_media(client, file_path)
        print("[TRANSCRIPTION] Gemini transcription completed.")
        print(f"[TRANSCRIPTION] Transcript characters: {len(transcript)}")
        return {
            "text": transcript,
            "segments": [],
            "language": "unknown",
            "duration": duration,
        }

    # MP4: only a real video needs local extraction. Audio-only MP4s (no
    # video stream) are sent directly, which already works today.
    if extension == ".mp4":
        if not _media_has_video(file_path):
            print("[TRANSCRIPTION] Audio-only MP4. Uploading directly to Gemini.")
            transcript = _transcribe_audio_media(client, file_path)
            print("[TRANSCRIPTION] Gemini transcription completed.")
            print(f"[TRANSCRIPTION] Transcript characters: {len(transcript)}")
            return {
                "text": transcript,
                "segments": [],
                "language": "unknown",
                "duration": duration,
            }

        # Real video: extract ONLY the audio with FFmpeg, then transcribe that.
        print("[TRANSCRIPTION] Real video detected. Extracting audio with FFmpeg...")

        temp_dir = tempfile.mkdtemp(prefix="ttt_audio_")
        temp_audio = os.path.join(temp_dir, "extracted_audio.mp3")
        try:
            _extract_audio_ffmpeg(file_path, temp_audio)
            print("[TRANSCRIPTION] Audio extraction complete.")

            transcript = _transcribe_audio_media(client, temp_audio)
            print("[TRANSCRIPTION] Gemini transcription completed.")
            print(f"[TRANSCRIPTION] Transcript characters: {len(transcript)}")
            return {
                "text": transcript,
                "segments": [],
                "language": "unknown",
                "duration": duration,
            }
        finally:
            # Always delete the temporary extracted audio, even when Gemini
            # or FFmpeg fails.
            try:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            print("[TRANSCRIPTION] Cleaning temporary audio file...")

    # Unsupported type: keep the bytecode happy and raise a clear error.
    raise RuntimeError(
        f"Unsupported media type '{extension}'. "
        "Supported formats: .mp3, .wav, .mp4"
    )

# Hesitation sounds that are safe to remove as whole words.
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
    r"\[(?:music|applause|laughter|laughs|coughing|background noise|"
    r"silence|indistinct|inaudible|pause)\]|"
    r"\((?:music|applause|laughter|laughs|coughing|background noise|"
    r"silence|indistinct|inaudible|pause)\)",
    re.IGNORECASE,
)


def clean_transcript(raw_text):
    """
    Clean the transcript for display/analysis.

    Important:
    This function does NOT modify transcript_raw.
    """

    text = raw_text or ""

    text = ARTIFACT_PATTERNS.sub("", text)

    filler_inline = "|".join(
        re.escape(word) for word in FILLER_WORDS
    )

    text = re.sub(
        r",\s*(?:" + filler_inline + r")\s*,",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r",\s*you\s+know\s*,",
        "",
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

    text = re.sub(
        r",\s*like\s*,",
        "",
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

    for filler in FILLER_WORDS:
        text = re.sub(
            r"\b" + re.escape(filler) + r"\b",
            "",
            text,
            flags=re.IGNORECASE,
        )

    text = re.sub(
        r"\b(\w+)(\s+\1){2,}\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    for word in SAFE_DOUBLE_WORDS:
        text = re.sub(
            r"\b" + re.escape(word) +
            r"\b(\s+" + re.escape(word) + r"\b)",
            word,
            text,
            flags=re.IGNORECASE,
        )

    text = _remove_duplicate_sentences(text)

    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    text = re.sub(r"^[\s,.;:?!]+", "", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def _remove_duplicate_sentences(text):
    """
    Remove an exact consecutive duplicate sentence.
    """

    pieces = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
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

        kept.append(current)
        previous = current

    return " ".join(
        piece for piece in kept
        if piece
    )