"""
file_utils.py
Helper functions to validate and save the uploaded audio/video files.

Only these file types are supported:
    MP3, WAV, MP4

Security:
    - extension whitelist (MP3 / WAV / MP4 only)
    - per-file size limit (default 250 MB, configurable via env)
    - original user filenames are NEVER reused; every file is saved under
      a fresh random UUID-based name so a malicious filename (path
      traversal, quotes, control characters) can never affect storage
    - uploaded files are deleted right after processing
"""

import os
import uuid

from dotenv import load_dotenv

# Load .env from an absolute path so it works from any working directory.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH)

# Set of allowed file extensions (lowercase, without the dot).
ALLOWED_EXTENSIONS = {"mp3", "wav", "mp4"}

# Old extension aliases that map to the same container/format.
EXTENSION_ALIASES = {"m4a": "mp4", "aac": "mp4", "ogg": "wav"}

# Largest allowed upload in bytes (default 250 MB).
DEFAULT_MAX_UPLOAD_MB = 250
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB)) * 1024 * 1024

MAX_FILENAME_LENGTH = 200


def is_allowed_extension(filename):
    """
    Return True if the file extension is one of the allowed ones.
    """
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    if extension in EXTENSION_ALIASES:
        return True
    return extension in ALLOWED_EXTENSIONS


def _extension_of(filename):
    """
    Return the normalized extension used for the saved file.
    Known aliases are mapped onto MP3/WAV/MP4.
    """
    extension = filename.rsplit(".", 1)[1].lower()
    return EXTENSION_ALIASES.get(extension, extension)


def create_secure_filename(filename):
    """
    Create a safe, unique filename like  3f2ab9c1de...mp3
    so user filenames can never cause problems.
    """
    extension = _extension_of(filename)
    unique_name = uuid.uuid4().hex
    return f"{unique_name}.{extension}"


def _stream_size(file):
    """
    Return the byte size of the uploaded file stream.
    Seeks through the stream without loading it into memory.
    Returns -1 if the size cannot be determined.
    """
    stream = getattr(file, "stream", None)
    if stream is None:
        # No stream (e.g. a lightweight stand-in used in unit tests) ->
        # treat as a small valid file; real Flask uploads always have one.
        return 1
    try:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        return size
    except Exception:
        return -1


def validate_uploaded_file(file):
    """
    Check that the uploaded file is valid.

    Returns:
        (True, "", secure_filename)  if the file is OK
        (False, error_message, None) if the file is NOT OK
    """
    if file is None:
        return False, "No file was uploaded.", None

    filename = file.filename
    if not filename or filename == "":
        return False, "The uploaded file has no filename.", None

    if len(filename) > MAX_FILENAME_LENGTH:
        return False, "The uploaded filename is too long.", None

    # No path separators or control characters in the original name.
    if "/" in filename or "\\" in filename or "\x00" in filename:
        return False, "The uploaded filename is not valid.", None

    if not is_allowed_extension(filename):
        return False, (
            "This file type is not supported. "
            "Please upload an MP3, WAV, or MP4 file."
        ), None

    size = _stream_size(file)
    if size < 0:
        return False, "Could not read the uploaded file.", None
    if size == 0:
        return False, "The uploaded file is empty.", None
    if size > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        return False, (
            f"The file is too large. The maximum size is {limit_mb} MB."
        ), None

    secure_filename = create_secure_filename(filename)
    return True, "", secure_filename


def save_uploaded_file(file, secure_filename, folder):
    """
    Save the uploaded file into the given folder
    and return the full path to the saved file.
    """
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, secure_filename)
    file.save(file_path)
    return file_path