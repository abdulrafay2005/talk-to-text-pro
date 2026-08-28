# Accuracy measurement

TalkToText-Pro does **not** hard-code or fake an accuracy number. Accuracy is
measured where it can be measured, and honestly described where it cannot.

## The two stages

### 1. Automatic Speech Recognition (ASR)
`faster-whisper <https://github.com/SYSTRAN/faster-whisper>`_ turns audio into
text. The model size comes from `WHISPER_MODEL` in `backend/.env`
(default: `base`).

- This project does **not** bundle an audio corpus, so we cannot claim a
  specific ASR word-error-rate for your recordings.
- Accuracy here depends on the model size and the audio itself. Using
  `WHISPER_MODEL=medium` or `large` raises ASR accuracy on clean speech but
  needs more disk/RAM and is slower.
- If you want a real ASR number, run `faster-whisper` on your labeled audio
  and compare with `tests/accuracy_evaluation.py:evaluate(reference, asr_text)`.

### 2. Text processing (cleaning + optimization)
After ASR, the transcript is cleaned (`backend/ai/transcription.py`) and,
when large, compressed/chunked for the AI (`backend/utils/token_utils.py`).

This stage is measured against gold-standard sample transcripts in
`tests/accuracy_evaluation.py` using two standard metrics:

- **Word Error Rate (WER)** – `(insertions + deletions + substitutions) /
  reference_words`, computed with word-level Levenshtein dynamic programming.
  `0%` means the processed text exactly matches the reference.
- **Content coverage** – the share of reference words that survive
  processing. `100%` means no meaningful content (decisions, deadlines,
  actions, speaker labels, order) was dropped.

The raw sample inputs contain only realistic noise (filler words,
repetitions, `[music]` / `(applause)` artifacts), so the measured WER and
coverage show how faithfully the cleaner reproduces the ideal transcript.
Result for the included samples: **average coverage 100%, average WER 0%**
(see the printed report from `python accuracy_evaluation.py`).

## Running the evaluation

```
cd tests
python accuracy_evaluation.py        # prints the report
python -m unittest test_pipeline_accuracy -v
python -m unittest test_cleaning -v
```

## What we guarantee (and what we don't)

- Guaranteed: cleaning removes only filler/artifacts and preserves speaker
  labels, decisions, action items, deadlines, technical terms, and order.
- Not claimed: an ASR accuracy percentage. Whisper `base` on hard audio will
  be well below 90%; that is a real limitation, not a number we fabricate.
  Raise `WHISPER_MODEL` for better ASR and measure it with the script above.