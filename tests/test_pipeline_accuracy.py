"""
test_pipeline_accuracy.py
Verifies the text-processing (cleaning) accuracy against gold-standard
sample transcripts using Word Error Rate (WER) and content coverage.

The ASR stage (faster-whisper) is NOT tested here because we do not ship
an audio corpus. ASR accuracy depends on WHISPER_MODEL and the audio;
use accuracy_evaluation.evaluate(reference, asr_text) on real data for
that measurement. This test measures the guarantee that cleaning removes
only filler/artifacts and NEVER drops meaningful content.

Run with:  python -m unittest test_pipeline_accuracy -v
"""

import os
import sys
import unittest

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ai.transcription import clean_transcript
from accuracy_evaluation import SAMPLES, evaluate


class CleaningAccuracyTests(unittest.TestCase):

    def test_cleaning_is_close_to_gold_reference(self):
        # For gold samples, the cleaning stage should reproduce the reference
        # almost exactly (input contains only fillers/artifacts + that content).
        for sample in SAMPLES:
            with self.subTest(sample=sample["name"]):
                cleaned = clean_transcript(sample["raw"])
                metrics = evaluate(sample["reference"], cleaned)
                self.assertLessEqual(
                    metrics["wer"], 0.05,
                    "Cleaning WER too high for '%s': %s"
                    % (sample["name"], metrics),
                )

    def test_no_meaningful_content_is_dropped(self):
        # Every reference word must survive cleaning (coverage >= 99%).
        for sample in SAMPLES:
            with self.subTest(sample=sample["name"]):
                cleaned = clean_transcript(sample["raw"])
                metrics = evaluate(sample["reference"], cleaned)
                self.assertGreaterEqual(
                    metrics["coverage"], 0.99,
                    "Content dropped for '%s': %s"
                    % (sample["name"], metrics),
                )

    def test_meaningful_details_are_preserved(self):
        # Speaker labels, deadlines, decisions and order must survive.
        cleaned = clean_transcript(
            "Um, Speaker 1: The budget deadline is March 15th. "
            "You know, Speaker 2: We decided to hire two engineers (applause). "
            "Speaker 1: Action item: basically, ship the API by Friday."
        )
        self.assertIn("Speaker 1:", cleaned)
        self.assertIn("Speaker 2:", cleaned)
        self.assertIn("deadline is March 15th.", cleaned)
        self.assertIn("decided to hire two engineers", cleaned)
        self.assertIn("Action item: ship the API by Friday", cleaned)

    def test_wer_metric_implementation(self):
        # A mistake in the metric itself must never report fake 100% accuracy.
        self.assertEqual(
            evaluate("hello world", "hello world")["wer"],
            0.0,
        )
        self.assertGreater(
            evaluate("hello world", "goodbye moon")["wer"],
            0.0,
        )
        # Dropping the whole reference reports the lowest possible accuracy.
        self.assertEqual(
            evaluate("one two three", "")["coverage"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()