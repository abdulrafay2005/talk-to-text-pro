"""
test_cleaning.py
Checks the transcript cleaning rules:

    - remove obvious filler words ("um", "uh", "you know", "like", ...)
    - remove repetitions (3+ repeats, or 2 repeats of filler words)
    - remove pure artifacts ([music], (applause), ...)
    - NEVER remove meaningful speech / speaker labels / deadlines /
      decisions / action items / important context
    - preserve chronological order and meaning

Run with:  python -m unittest test_cleaning -v
"""

import os
import sys
import unittest

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ai.transcription import clean_transcript


class FillerRemovalTests(unittest.TestCase):

    def test_removes_common_hesitation_sounds(self):
        cleaned = clean_transcript(
            "Um, we need to ship it. Uh, can we test this week? Hmm."
        )
        self.assertNotIn("Um", cleaned)
        self.assertNotIn(", uh", cleaned)
        self.assertNotIn("Hmm", cleaned)
        self.assertIn("we need to ship it.", cleaned)
        self.assertIn("can we test this week?", cleaned)

    def test_removes_you_know_only_as_filler(self):
        cleaned = clean_transcript(
            "You know, the deadline is Friday. Do you know the answer?"
        )
        # The filler "You know," at the start is gone...
        self.assertNotIn("You know,", cleaned)
        # ...but the real question "Do you know the answer?" is untouched.
        self.assertIn("Do you know the answer?", cleaned)

    def test_removes_filler_like_but_not_meaningful_like(self):
        cleaned = clean_transcript(
            "We, like, decided to expand. Ali likes the new design."
        )
        self.assertNotIn("We, like, decided", cleaned)
        self.assertIn("We decided to expand", cleaned)
        self.assertIn("Ali likes the new design.", cleaned)

    def test_removes_filler_basically_but_not_real_use(self):
        cleaned = clean_transcript(
            "Basically, we are ready. It is basically done."
        )
        self.assertNotIn("Basically,", cleaned)
        # "It is basically done" has no comma -> real meaning, left alone.
        self.assertIn("It is basically done.", cleaned)


class RepetitionRemovalTests(unittest.TestCase):

    def test_collapses_three_plus_repeats(self):
        self.assertIn(
            "The build is very ready",
            clean_transcript("The build is very very very ready"),
        )

    def test_collapses_double_filler_words(self):
        cleaned = clean_transcript("Okay okay, we agree. Yeah yeah, right.")
        self.assertNotIn("Okay okay", cleaned)
        self.assertNotIn("Yeah yeah", cleaned)

    def test_never_removes_meaningful_doubles(self):
        # "had had" / "that that" are real English, never collapsed.
        self.assertIn(
            "He had had enough.",
            clean_transcript("He had had enough."),
        )

    def test_removes_exact_duplicate_sentences(self):
        cleaned = clean_transcript(
            "The launch is on Monday. The launch is on Monday. Everyone agreed."
        )
        self.assertEqual(cleaned.count("The launch is on Monday."), 1)
        self.assertIn("Everyone agreed.", cleaned)


class ArtifactRemovalTests(unittest.TestCase):

    def test_removes_transcript_artifacts(self):
        cleaned = clean_transcript(
            "Speaker 1: We signed the deal. [music] (applause)"
        )
        self.assertNotIn("[music]", cleaned)
        self.assertNotIn("(applause)", cleaned)
        self.assertIn("We signed the deal.", cleaned)

    def test_unknown_brackets_survive(self):
        # Only known artifact patterns are removed. Something else in
        # brackets is treated as content and kept.
        cleaned = clean_transcript("The [budget] was approved.")
        self.assertIn("[budget]", cleaned)


class ContentPreservationTests(unittest.TestCase):

    def test_speaker_names_labels_and_details_survive(self):
        raw = (
            "Um, Ali: The deadline is March 15th. "
            "Sarah: We decided to hire two engineers. "
            "Ali: Action item: ship the API by Friday. "
            "Sarah: Agreed."
        )
        cleaned = clean_transcript(raw)

        self.assertIn("Ali:", cleaned)
        self.assertIn("Sarah:", cleaned)
        self.assertIn("The deadline is March 15th.", cleaned)
        self.assertIn("We decided to hire two engineers.", cleaned)
        self.assertIn("Action item: ship the API by Friday.", cleaned)
        self.assertIn("Agreed.", cleaned)

    def test_chronological_order_is_preserved(self):
        raw = (
            "First we set the budget. Then we chose a vendor. "
            "Finally we scheduled the launch."
        )
        cleaned = clean_transcript(raw)

        positions = [
            cleaned.find("set the budget"),
            cleaned.find("chose a vendor"),
            cleaned.find("scheduled the launch"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_cleaner_never_loses_the_point(self):
        original_point = "Decision: increase the price to two hundred dollars."
        cleaned = clean_transcript("uh " + original_point)
        self.assertIn(original_point, cleaned)


if __name__ == "__main__":
    unittest.main()