"""
test_sharing.py
Checks the share-link security helpers (pure functions, no DB needed):

    - tokens are long, random and unguessable
    - invalid / hostile tokens are rejected BEFORE any query runs
    - share URLs are built only from valid tokens

Run with:  python -m unittest test_sharing -v
"""

import os
import sys
import unittest

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.sharing import (
    build_share_url,
    generate_share_token,
    is_valid_share_token,
)


class ShareTokenTests(unittest.TestCase):

    def test_tokens_are_random_long_and_unique(self):
        tokens = {generate_share_token() for _ in range(25)}
        self.assertEqual(len(tokens), 25, "Tokens must be unique")
        for token in tokens:
            self.assertGreaterEqual(len(token), 20)
            self.assertTrue(is_valid_share_token(token))

    def test_valid_token_accepted(self):
        token = generate_share_token()
        self.assertTrue(is_valid_share_token(token))

    def test_invalid_and_hostile_inputs_rejected(self):
        invalid = [
            None,
            12345,
            "",
            "short",
            "a" * 1000,
            "abc' OR '1'=='1",
            '{"$gt": ""}',
            "SELECT * FROM meetings",
            "token with spaces",
            "token;DROP",
            "token..//..",
            "😀" * 22,
        ]
        for bad in invalid:
            with self.subTest(bad=bad):
                self.assertFalse(
                    is_valid_share_token(bad),
                    "Hostile token should be rejected: %r" % (bad,),
                )


class ShareUrlTests(unittest.TestCase):

    def test_url_built_from_valid_token(self):
        token = generate_share_token()
        self.assertEqual(
            build_share_url(token, "http://localhost:5173/"),
            "http://localhost:5173/share/" + token,
        )

    def test_url_never_built_from_invalid_token(self):
        self.assertIsNone(build_share_url("bad token!", "http://x.com"))
        self.assertIsNone(build_share_url("", "http://x.com"))
        self.assertIsNone(build_share_url(None, "http://x.com"))


if __name__ == "__main__":
    unittest.main()