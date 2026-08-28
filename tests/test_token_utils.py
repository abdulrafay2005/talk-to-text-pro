"""
Tests for the text & token optimization system.

Covers:
    - short transcript below the token limit
    - transcript exactly at the token limit
    - transcript above the token limit (smart chunking)
    - large transcript requiring multiple chunks
    - empty transcript
    - token savings calculation
    - reduction percentage calculation
    - no negative token savings
    - statistics survive the backend -> API -> frontend round trip

Run them with:
    python test_token_utils.py
    (or:  python -m unittest test_token_utils test_file_utils -v)
"""

import os
import sys
import unittest

from bson import ObjectId

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.token_utils import (
    build_optimization_stats,
    count_words,
    estimate_tokens,
    optimize_for_tokens,
    optimized_text_for,
    split_sentences,
)
from models.meeting import create_meeting_document, convert_meeting_to_view


class TokenEstimationTests(unittest.TestCase):

    def test_empty_text_is_zero_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("   "), 0)
        self.assertEqual(estimate_tokens(None), 0)

    def test_char_based_estimate(self):
        # ~4 characters per token.
        self.assertEqual(estimate_tokens("a" * 400), 100)
        self.assertEqual(estimate_tokens("a" * 8), 2)

    def test_non_empty_text_has_at_least_one_token(self):
        self.assertEqual(estimate_tokens("a"), 1)

    def test_word_count(self):
        self.assertEqual(count_words("one two   three\nfour"), 4)
        self.assertEqual(count_words(""), 0)


class OptimizeWithinLimitTests(unittest.TestCase):

    def test_short_transcript_returns_original_unchanged(self):
        text = "This is a short meeting about the project schedule."
        chunks = optimize_for_tokens(text, 1000)
        self.assertEqual(chunks, [text])

    def test_transcript_exactly_at_limit_is_unchanged(self):
        text = ("We reviewed the plan. " * 12).strip()
        limit = estimate_tokens(text)
        chunks = optimize_for_tokens(text, limit)
        self.assertEqual(chunks, [text])

    def test_below_limit_stats_report_no_optimization(self):
        text = "Short meeting transcript with only a couple of sentences."
        stats = build_optimization_stats(text, 1000)
        self.assertFalse(stats["optimization_applied"])
        self.assertEqual(stats["tokens_saved"], 0)
        self.assertEqual(stats["reduction_percent"], 0.0)
        self.assertEqual(stats["chunks_created"], 1)
        self.assertEqual(stats["original_tokens"], stats["optimized_tokens"])
        self.assertEqual(stats["original_words"], stats["optimized_words"])


class OptimizeOverLimitTests(unittest.TestCase):

    def test_every_chunk_fits_inside_max_tokens(self):
        text = ("The team decided to ship the feature next week. " * 40).strip()
        max_tokens = 20
        chunks = optimize_for_tokens(text, max_tokens)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(
                estimate_tokens(chunk),
                max_tokens,
                "Chunk exceeds the token limit: %r" % chunk[:60],
            )

    def test_large_transcript_creates_multiple_chunks(self):
        text = ("Decision one approved by the group. " * 60).strip()
        chunks = optimize_for_tokens(text, 30)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(estimate_tokens(chunk), 30)

    def test_content_and_order_are_preserved(self):
        sentences = [
            "First we discussed the budget.",
            "Second we agreed on the timeline.",
            "Third we assigned the tasks.",
            "Fourth we set the launch date.",
        ]
        text = " ".join(sentences)
        chunks = optimize_for_tokens(text, 12)
        self.assertGreater(len(chunks), 1)

        joined = "\n".join(chunks)
        for sentence in sentences:
            self.assertIn(sentence, joined, "Sentence lost during optimization")

        # Chronological order must be preserved across chunks.
        positions = [joined.find(sentence) for sentence in sentences]
        self.assertEqual(positions, sorted(positions))

    def test_speaker_labels_are_preserved(self):
        line = "Speaker 1: We decided to increase the marketing budget."
        text = "\n".join([line] * 40)
        chunks = optimize_for_tokens(text, 15)
        joined = "\n".join(chunks)
        self.assertIn("Speaker 1:", joined)

    def test_compression_removes_only_artifacts(self):
        text = (
            "Ali said we should keep the API. [music]  \n"
            "Decisions: launch in June. (applause)\n"
        )
        text = (text * 30).strip()
        stats = build_optimization_stats(text, 50)
        self.assertTrue(stats["optimization_applied"])
        self.assertGreater(stats["tokens_saved"], 0)
        # Real content is never removed.
        joined = "\n".join(stats_chunks(text, 50))
        self.assertIn("Decisions: launch in June.", joined)
        self.assertIn("Ali said we should keep the API.", joined)


def stats_chunks(text, max_tokens):
    """Helper: return the optimized chunks produced for a text/limit."""
    return optimize_for_tokens(text, max_tokens)


class StatsCalculationTests(unittest.TestCase):

    def test_tokens_saved_formula(self):
        text = ("Ali confirmed the deadline is Friday. [music] " * 25).strip()
        stats = build_optimization_stats(text, 15)
        expected = stats["original_tokens"] - stats["optimized_tokens"]
        self.assertEqual(stats["tokens_saved"], max(0, expected))
        self.assertGreaterEqual(stats["tokens_saved"], 0)

    def test_reduction_percent_formula(self):
        text = ("Ali confirmed the deadline is Friday. [music] " * 25).strip()
        stats = build_optimization_stats(text, 15)
        expected = (
            (stats["original_tokens"] - stats["optimized_tokens"])
            / stats["original_tokens"]
        ) * 100
        self.assertAlmostEqual(stats["reduction_percent"], round(expected, 1), places=1)

    def test_no_negative_savings(self):
        # A wall of varied text with nothing compressible cannot go negative.
        text = ("unique words here to fill space " * 40).strip()
        stats = build_optimization_stats(text, 20)
        self.assertGreaterEqual(stats["tokens_saved"], 0)
        self.assertEqual(
            stats["tokens_saved"],
            max(0, stats["original_tokens"] - stats["optimized_tokens"]),
        )

    def test_empty_transcript_stats_are_zero(self):
        stats = build_optimization_stats("", 3000)
        self.assertEqual(stats["original_tokens"], 0)
        self.assertEqual(stats["optimized_tokens"], 0)
        self.assertEqual(stats["tokens_saved"], 0)
        self.assertEqual(stats["reduction_percent"], 0.0)
        self.assertFalse(stats["optimization_applied"])
        self.assertEqual(stats["chunks_created"], 0)
        self.assertEqual(stats["original_words"], 0)
        self.assertEqual(stats["optimized_words"], 0)

    def test_empty_transcript_produces_no_chunks(self):
        self.assertEqual(optimize_for_tokens("", 3000), [])
        self.assertEqual(optimize_for_tokens(None, 3000), [])


class RoundTripConsistencyTests(unittest.TestCase):

    def test_stats_survive_meeting_round_trip(self):
        text = ("Ali confirmed the deadline is Friday. [music] " * 25).strip()
        stats = build_optimization_stats(text, 15)

        meeting = create_meeting_document(
            title="Round Trip",
            transcription={
                "text": text,
                "segments": [],
                "language": "en",
                "duration": 10.0,
            },
            cleaned_text=text,
            translated_text=None,
            translate_to=None,
            analysis={
                "meeting_type": "General Meeting",
                "summary": "Not specified",
                "key_points": [],
                "topics": [],
                "decisions": [],
                "action_items": [],
                "unresolved_issues": [],
                "sentiment": "Neutral",
            },
            user_id=None,
            optimization=stats,
        )

        # A real insert assigns the document its ObjectId.
        meeting["_id"] = ObjectId()

        view = convert_meeting_to_view(meeting)

        stored = view["optimization"]
        for key in [
            "original_tokens",
            "optimized_tokens",
            "tokens_saved",
            "reduction_percent",
            "original_words",
            "optimized_words",
            "optimization_applied",
            "chunks_created",
        ]:
            self.assertEqual(
                stored[key],
                stats[key],
                "Optimization field '%s' changed during the round trip" % key,
            )

    def test_frontend_values_match_backend_formulas(self):
        text = ("Ali confirmed the deadline is Friday. [music] " * 25).strip()
        stats = build_optimization_stats(text, 15)

        # The frontend displays exactly these fields from the backend.
        original_tokens = stats["original_tokens"]
        optimized_tokens = stats["optimized_tokens"]
        self.assertEqual(
            stats["tokens_saved"],
            max(0, original_tokens - optimized_tokens),
        )
        self.assertEqual(
            stats["reduction_percent"],
            round(max(0, original_tokens - optimized_tokens) / original_tokens * 100, 1),
        )


class SentenceSplitTests(unittest.TestCase):

    def test_splits_on_sentence_boundaries(self):
        pieces = split_sentences("Hello world. Goodbye world! Really?")
        self.assertEqual(pieces, ["Hello world.", "Goodbye world!", "Really?"])


class TranscriptIsolationTests(unittest.TestCase):
    """
    The whole point of the optimization feature:

        Original/Clean Transcript -> stored & shown to the user
        Optimized Transcript      -> AI analysis only
        Optimization Stats        -> computed from the optimization input/output

    The compressed/chunked text must NEVER replace what the user reads.
    """

    def _over_limit_transcript(self, max_tokens):
        lines = [
            "Speaker 1:  The budget deadline is March 15th.  [music]",
            "Speaker 2: We decided to hire two engineers. (applause)",
            "Speaker 1: Action item:  ship the API by Friday.",
            "Speaker 2:  Agreed, the launch date is June 2nd.",
        ]
        # Heavy cleanup being simulated by a light normalization step (the
        # stored & displayed version keeps only the spoken words, like the
        # real pipeline's clean_transcript does).
        raw = "\n".join(lines) + "\n"
        cleaned = "\n".join(" ".join(line.split()) for line in lines)
        self.assertGreater(estimate_tokens(cleaned), max_tokens)
        return raw, cleaned

    def _build_meeting(self, raw, cleaned, max_tokens):
        optimization = build_optimization_stats(cleaned, max_tokens)
        analysis = {
            "meeting_type": "General Meeting",
            "summary": "Not specified",
            "key_points": [],
            "topics": [],
            "decisions": [],
            "action_items": [],
            "unresolved_issues": [],
            "sentiment": "Neutral",
        }
        meeting = create_meeting_document(
            title="Isolation Check",
            transcription={
                "text": raw,
                "segments": [],
                "language": "en",
                "duration": 30.0,
            },
            cleaned_text=cleaned,
            translated_text=None,
            translate_to=None,
            analysis=analysis,
            user_id=None,
            optimization=optimization,
            optimized_text=optimized_text_for(cleaned, max_tokens),
        )
        meeting["_id"] = ObjectId()
        return convert_meeting_to_view(meeting)

    def test_optimized_text_never_overwrites_the_stored_transcript(self):
        max_tokens = 40
        raw, cleaned = self._over_limit_transcript(max_tokens)

        # The AI input really does get optimized here (compressed + chunked).
        chunks = optimize_for_tokens(cleaned, max_tokens)
        optimized_text = "\n\n".join(chunks)
        self.assertNotEqual(optimized_text, cleaned)
        self.assertGreater(len(chunks), 1)
        self.assertNotIn("[music]", optimized_text)
        self.assertNotIn("(applause)", optimized_text)
        self.assertNotIn("  ", optimized_text)

        view = self._build_meeting(raw, cleaned, max_tokens)

        # Stored & displayed transcripts stay 100% verbatim.
        self.assertEqual(view["transcript_raw"], raw)
        self.assertEqual(view["transcript_cleaned"], cleaned)
        self.assertNotEqual(view["transcript_cleaned"], optimized_text)

        # The AI-optimized version lives in its OWN separate field so the
        # user's transcript can never be confused with the AI analysis input.
        self.assertEqual(view["transcript_optimized"], optimized_text)

        # No OTHER stored string field may contain the optimized text.
        for key, value in view.items():
            if key.startswith("transcript_") or key in ("translated_transcript",):
                continue
            if isinstance(value, str):
                self.assertNotEqual(
                    value, optimized_text,
                    "Optimized text leaked into stored field '%s'" % key,
                )

        # Meaningful spoken content survives in the DISPLAYED transcript:
        # speaker labels, decisions, action item, deadlines, order.
        shown = view["transcript_cleaned"]
        self.assertIn("Speaker 1:", shown)
        self.assertIn("Speaker 2:", shown)
        self.assertIn("The budget deadline is March 15th.", shown)
        self.assertIn("We decided to hire two engineers.", shown)
        self.assertIn("Action item: ship the API by Friday.", shown)
        self.assertIn("Agreed, the launch date is June 2nd.", shown)
        positions = [
            shown.find("deadline is March 15th"),
            shown.find("decided to hire two"),
            shown.find("ship the API by Friday"),
            shown.find("launch date is June 2nd"),
        ]
        self.assertEqual(positions, sorted(positions),
                         "Chronological order broken in displayed transcript")

    def test_optimized_chunks_keep_meaningful_content_and_drop_only_artifacts(self):
        max_tokens = 40
        _, cleaned = self._over_limit_transcript(max_tokens)
        chunks = optimize_for_tokens(cleaned, max_tokens)

        self.assertFalse(any("[music]" in c or "(applause)" in c or "  " in c
                             for c in chunks))
        joined = "\n".join(chunks)
        for phrase in [
            "Speaker 1:",
            "Speaker 2:",
            "deadline is March 15th",
            "decided to hire two engineers",
            "ship the API by Friday",
            "launch date is June 2nd",
        ]:
            self.assertIn(phrase, joined, "Meaningful content lost during optimization")

    def test_optimization_field_contains_stats_only(self):
        max_tokens = 40
        raw, cleaned = self._over_limit_transcript(max_tokens)
        view = self._build_meeting(raw, cleaned, max_tokens)

        opt = view["optimization"]
        self.assertTrue(opt["optimization_applied"])
        self.assertGreater(opt["chunks_created"], 1)
        # Stats only: no transcript text ever stored under "optimization".
        self.assertFalse({k: v for k, v in opt.items() if isinstance(v, str)})

    def test_transcript_under_token_limit_is_stored_untouched(self):
        cleaned = (
            "Speaker 1: We need the API finished by Friday. "
            "Speaker 2: Agreed, and the launch is on June 2nd."
        )
        max_tokens = 3000  # production MAX_ANALYSIS_TOKENS

        optimization = build_optimization_stats(cleaned, max_tokens)
        self.assertFalse(optimization["optimization_applied"])
        self.assertEqual(optimization["tokens_saved"], 0)
        # Below the limit the optimizer returns the original unchanged.
        self.assertEqual(optimize_for_tokens(cleaned, max_tokens), [cleaned])

        view = self._build_meeting(cleaned, cleaned, max_tokens)
        self.assertEqual(view["transcript_cleaned"], cleaned)
        self.assertEqual(view["transcript_raw"], cleaned)
        # Under the limit the optimized version equals the cleaned transcript.
        self.assertEqual(view["transcript_optimized"], cleaned)


if __name__ == "__main__":
    unittest.main()