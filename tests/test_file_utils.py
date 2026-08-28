"""
Simple tests for the file validation logic.

Run them with:
    python test_file_utils.py
"""

import os
import sys
import unittest

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.file_utils import is_allowed_extension, validate_uploaded_file


class FakeFile:
    """A tiny stand-in for an uploaded file. It only has a filename."""

    def __init__(self, filename):
        self.filename = filename


class FileUtilsTests(unittest.TestCase):

    def test_valid_mp3(self):
        is_valid, error, filename = validate_uploaded_file(FakeFile("speech.mp3"))
        self.assertTrue(is_valid)
        self.assertTrue(filename.endswith(".mp3"))

    def test_valid_extensions(self):
        self.assertTrue(is_allowed_extension("audio.wav"))
        self.assertTrue(is_allowed_extension("video.mp4"))

    def test_uppercase_extension_is_accepted(self):
        self.assertTrue(is_allowed_extension("speech.MP3"))

    def test_invalid_extension_is_rejected(self):
        is_valid, error, filename = validate_uploaded_file(FakeFile("notes.txt"))
        self.assertFalse(is_valid)
        self.assertIn("not supported", error)

    def test_no_file_is_rejected(self):
        is_valid, error, filename = validate_uploaded_file(None)
        self.assertFalse(is_valid)

    def test_empty_filename_is_rejected(self):
        is_valid, error, filename = validate_uploaded_file(FakeFile(""))
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()