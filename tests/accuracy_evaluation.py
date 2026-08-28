"""
accuracy_evaluation.py
========================
Makes the "accuracy" of the TalkToText-Pro text pipeline MEASURABLE.

What is measured here
---------------------
TWO things, computed with the standard Word Error Rate (WER) metric plus a
content-retention metric:

  1. Cleaning accuracy  : how close clean_transcript(raw) is to a gold-standard
                          reference transcript. Filler ("um", "uh", "you know"),
                          repetitions and artifacts must be removed WITHOUT
                          losing decisions, deadlines, actions, speaker labels
                          or chronological order. A perfect cleaner scores
                          WER ~ 0% and coverage ~ 100%.

  2. Content retention  : the share of reference words that survive processing.
                          This directly tests the "do not delete meaningful
                          speech" guarantee.

What is NOT measured (and why)
------------------------------
The automatic speech recognition (ASR) stage uses faster-whisper (model size
comes from WHISPER_MODEL in backend/.env, default "base"). We do NOT ship a
real audio corpus, so we cannot truthfully claim an ASR WER number for your
specific recordings here. That is why we never hard-code or print a made-up
"85-90% accuracy". Instead:

    - The evaluation below measures the whole text processing stage.
    - If you have real ASR transcripts (audio -> text) and their
      gold-standard references, you can measure the ASR stage yourself with
      the evaluate(reference, hypothesis) function in this file and compare
      the WER. Whisper "base" is a small model; larger models
      (WHISPER_MODEL=medium/large) give higher ASR accuracy on clean speech.

How accuracy is computed
------------------------
WER = (insertions + deletions + substitutions) / reference_words
      computed via word-level Levenshtein (standard dynamic programming).
Coverage = matched_reference_words / reference_words.

Run it with:
    python accuracy_evaluation.py
"""

import os
import sys
from collections import Counter

# Make the backend folder importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ai.transcription import clean_transcript
from utils.token_utils import estimate_tokens, optimize_for_tokens


def evaluate(reference, hypothesis):
    """
    Return accuracy metrics comparing a hypothesis text to a reference.

        wer     : Word Error Rate (0.0 = perfect)
        coverage: fraction of reference words present in the hypothesis
        ref_words, hyp_words: word counts
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not ref_words:
        return {"wer": 0.0, "coverage": 1.0, "ref_words": 0, "hyp_words": len(hyp_words)}

    distance = _levenshtein(ref_words, hyp_words)
    wer = distance / len(ref_words)
    coverage = _coverage(ref_words, hyp_words)

    return {
        "wer": round(wer, 4),
        "coverage": round(coverage, 4),
        "ref_words": len(ref_words),
        "hyp_words": len(hyp_words),
    }


def _levenshtein(a, b):
    """
    Classic Levenshtein edit distance over two sequences
    (here: word lists). O(n*m) - fine for transcripts.
    """
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, word_a in enumerate(a, 1):
        current = [i]
        for j, word_b in enumerate(b, 1):
            cost = 0 if word_a == word_b else 1
            current.append(min(
                current[j - 1] + 1,        # insertion
                previous[j] + 1,           # deletion
                previous[j - 1] + cost,    # substitution / match
            ))
        previous = current

    return previous[-1]


def _coverage(reference_words, hypothesis_words):
    """
    Fraction of reference word tokens that still exist in the hypothesis.
    1.0 means nothing meaningful was dropped.
    """
    hyp_counts = Counter(hypothesis_words)
    ref_counts = Counter(reference_words)

    matched = sum(
        min(count, hyp_counts.get(word, 0))
        for word, count in ref_counts.items()
    )
    total = sum(ref_counts.values())
    return matched / total if total else 1.0


# ---------------------------------------------------------------------------
# Sample evaluation: gold references vs "raw" ASR output full of fillers,
# repetitions and artifacts. The raw versions are realistic whisper output;
# the reference is the ideal transcript a human reviewer would accept after
# cleaning. Nothing is hard-coded: the metrics are computed below.
# ---------------------------------------------------------------------------

SAMPLES = [
    {
        "name": "project planning",
        "reference": (
            "Speaker 1: The budget deadline is March 15th. "
            "Speaker 2: We decided to hire two engineers. "
            "Speaker 1: Action item: ship the API by Friday. "
            "Speaker 2: Agreed agreed, the launch date is June 2nd."
        ),
        "raw": (
            "Um, uh Speaker 1: The budget deadline is March 15th. "
            "You know, Speaker 2: We, like, decided to hire two engineers "
            "(applause). Speaker 1: Action item: basically, ship the API by "
            "Friday. [music] Speaker 2: Agreed agreed, the launch date is "
            "June 2nd."
        ),
    },
    {
        "name": "status update",
        "reference": (
            "Speaker A: The staging build is ready. "
            "Speaker B: We postponed the demo until Monday. "
            "Speaker A: Decision: keep the feature flag on."
        ),
        "raw": (
            "Uh, Speaker A: The staging build is ready. "
            "Speaker B: We, you know, postponed the demo until Monday. "
            "Speaker A: Decision: keep the feature flag on. (laughter)"
        ),
    },
    {
        "name": "client review",
        "reference": (
            "Ali: We raised the price to two hundred dollars. "
            "Sarah: The client approved the new timeline. "
            "Ali: Deadline: final invoice by the end of the month."
        ),
        "raw": (
            "Ali: We raised the price to two hundred dollars. hmm "
            "Sarah: The client approved the new timeline. "
            "Ali: Deadline: final invoice by the end of the month. "
            "[silence]"
        ),
    },
]


def run_cleaning_evaluation():
    """
    Run clean_transcript on every sample's raw text and compare to its
    reference. Prints a table + an overall summary. Returns the metrics.
    """
    print("=" * 64)
    print("Text processing accuracy evaluation (clean_transcript)")
    print("=" * 64)

    rows = []
    for sample in SAMPLES:
        cleaned = clean_transcript(sample["raw"])
        metrics = evaluate(sample["reference"], cleaned)
        rows.append((sample["name"], cleaned, metrics))

        print(f"\n--- {sample['name']} ---")
        print(f"  Reference words : {metrics['ref_words']}")
        print(f"  Processed words : {metrics['hyp_words']}")
        print(f"  Coverage        : {metrics['coverage'] * 100:.1f}%")
        print(f"  WER (cleaning)  : {metrics['wer'] * 100:.1f}%")

    average_wer = sum(row[2]["wer"] for row in rows) / len(rows)
    average_coverage = sum(row[2]["coverage"] for row in rows) / len(rows)

    print("\n" + "=" * 64)
    print("Overall (text processing stage only)")
    print(f"  Average coverage : {average_coverage * 100:.1f}%")
    print(f"  Average WER      : {average_wer * 100:.1f}%")
    print("=" * 64)
    print(
        "NOTE: this measures the CLEANING stage. ASR accuracy depends on "
        "the Whisper model (WHISPER_MODEL) and the audio; measure it with "
        "evaluate(reference, your_asr_text) on real transcripts."
    )

    return rows


if __name__ == "__main__":
    run_cleaning_evaluation()