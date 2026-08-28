"""
token_utils.py
Helpers for the "Text & Token Optimization" feature:

    estimate_tokens(text)                 -> estimated AI token count (chars / 4)
    count_words(text)                     -> word count
    optimize_for_tokens(text, max_tokens) -> chunked text that fits inside `max_tokens`
    build_optimization_stats(text, max)   -> the optimization block saved in MongoDB

How the system is meant to behave (honest by design):

  1. When the transcript already fits inside `max_tokens`, NO compression is
     performed and the ORIGINAL text is returned unchanged. The stats then
     report tokens_saved = 0 and optimization_applied = False. We never claim
     token savings when no optimization happened.

  2. When the transcript exceeds `max_tokens`, a SAFE compression/normalization
     stage runs first. It only removes genuinely unnecessary text: repeated
     whitespace, trailing spaces, redundant punctuation, control/zero-width
     characters, and pure transcript artifacts such as "[music]" or
     "(applause)". It never deletes spoken meeting content, decisions,
     action items, deadlines, technical terms, or speaker labels.

  3. After compression the text is chunked at meaningful boundaries
     (speaker/paragraph first, then sentence, then word) so every chunk fits
     inside `max_tokens` while preserving the original chronological order.
     No content is ever dropped.

Token estimation is a simple character-based approximation
(~4 characters per token for English). It runs locally and instantly,
so we never need an external tokenizer or an OpenAI dependency.
"""

import re

# English text averages roughly 4 characters per token.
CHARS_PER_TOKEN = 4.0

WORD_PATTERN = re.compile(r"\S+")
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

# Pure transcript artifacts that carry no meeting content. These are
# ASR/editor conventions, not spoken words, so removing them is safe.
NOISE_PATTERNS = [
    re.compile(
        r"\[(?:music|applause|laughter|laughs|coughing|background noise|"
        r"silence|indistinct|inaudible|pause)\]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\((?:music|applause|laughter|laughs|coughing|background noise|"
        r"silence|indistinct|inaudible|pause)\)",
        re.IGNORECASE,
    ),
]

# Zero-width / soft-hyphen / BOM characters consume tokens but carry no meaning.
ZERO_WIDTH_OR_CONTROL = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
# Control characters we can safely delete (keeps newline \n and tab \t).
CONTROL_KEEP_NL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def count_words(text):
    """
    Count words using simple whitespace splitting.
    """
    text = text or ""
    return len(WORD_PATTERN.findall(text))


def estimate_tokens(text):
    """
    Estimate how many tokens a text will use for the AI model.
    Local approximation: len(text) / 4. Returns 0 for empty text.
    """
    text = text or ""
    if not text.strip():
        return 0
    return max(1, round(len(text) / CHARS_PER_TOKEN))


def split_sentences(text):
    """
    Split text into sentences on ". ", "! " or "? ".
    Returns non-empty pieces, trailing punctuation is preserved.
    """
    parts = SENTENCE_BOUNDARY.split(text.strip())
    return [piece.strip() for piece in parts if piece.strip()]


def _normalize_text(text):
    """
    SAFE compression/normalization stage. Only removes genuinely unnecessary
    text (whitespace, artifacts, redundant punctuation, control characters).
    Never deletes spoken content and never rewrites what people said.
    """
    text = text or ""

    # Remove zero-width / BOM characters that waste tokens.
    text = ZERO_WIDTH_OR_CONTROL.sub("", text)

    # Remove leftover control characters (keep newline and tab).
    text = CONTROL_KEEP_NL.sub("", text)

    # Remove pure transcript artifacts like [music] / (applause).
    for pattern in NOISE_PATTERNS:
        text = pattern.sub("", text)

    # Normalize line endings to \n.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse 3+ consecutive newlines into a single paragraph break.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse horizontal whitespace runs and trim every line.
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    text = "\n".join(lines)

    # Collapse runs of the same punctuation left behind by the removals
    # (keep an ellipsis as a single "…" character instead of three dots).
    text = re.sub(r"\.{3,}", "…", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r",{2,}", ",", text)

    # Remove a space that appears right before punctuation.
    text = re.sub(r"\s+([,.;:?!…])", r"\1", text)

    return text.strip()


def _split_plain(block, max_tokens):
    """
    Split a block of words into pieces that each fit inside max_tokens.
    Used only for extremely long sentences that cannot be split safely
    on sentence boundaries.
    """
    words = block.split()
    pieces = []
    current = []
    current_tokens = 0

    for word in words:
        word_tokens = estimate_tokens(word)

        if current and current_tokens + word_tokens > max_tokens:
            pieces.append(" ".join(current))
            current = []
            current_tokens = 0

        current.append(word)
        current_tokens += word_tokens

    if current:
        pieces.append(" ".join(current))

    # A single word is never above max_tokens for any realistic limit,
    # but if that ever happened we still keep the word (never drop content).
    return pieces or [block]


def _split_paragraph(paragraph, max_tokens):
    """
    Split one paragraph into ordered units that each fit inside max_tokens.
    Preserves speaker turns: the paragraph is first split on newlines
    (speaker labels often start a new line), then on sentences, then words.
    """
    lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
    units = []

    for line in lines:
        if estimate_tokens(line) <= max_tokens:
            units.append(line)
            continue

        sentences = split_sentences(line)

        if len(sentences) <= 1:
            units.extend(_split_plain(line, max_tokens))
            continue

        for sentence in sentences:
            if estimate_tokens(sentence) <= max_tokens:
                units.append(sentence)
            else:
                units.extend(_split_plain(sentence, max_tokens))

    return units


def _rejoin_units(units, max_tokens):
    """
    Greedily join ordered units back into chunks, keeping every chunk as
    close to max_tokens as possible without ever exceeding it.
    """
    chunks = []
    current = []
    current_tokens = 0

    for unit in units:
        unit_tokens = estimate_tokens(unit)

        if current and current_tokens + unit_tokens <= max_tokens:
            current.append(unit)
            current_tokens += unit_tokens
        else:
            if current:
                chunks.append("\n".join(current))
            current = [unit]
            current_tokens = unit_tokens

    if current:
        chunks.append("\n".join(current))

    return chunks


def _chunk_text(text, max_tokens):
    """
    Split a text that is too large into an ordered list of chunks so every
    chunk fits inside max_tokens and NO content is ever dropped.

    Boundaries are chosen in this order (most meaningful first):
        paragraph (blank line) -> speaker turn (newline) -> sentence -> word.
    """
    paragraphs = [p for p in text.split("\n\n") if p.strip()]

    units = []
    for paragraph in paragraphs:
        if estimate_tokens(paragraph) <= max_tokens:
            units.append(paragraph)
        else:
            units.extend(_split_paragraph(paragraph, max_tokens))

    return _rejoin_units(units, max_tokens)


def optimize_for_tokens(text, max_tokens):
    """
    Return the text as an ordered list of chunks, each inside max_tokens.

    - Empty text                          -> []
    - Text already within max_tokens      -> [original text] (unchanged)
    - Text over max_tokens                -> safely compressed, then chunked
      on speaker/paragraph/sentence boundaries.

    Compression only kicks in when it is necessary (the text exceeds the
    limit). When it is not necessary, the original text is returned
    unchanged so we never misrepresent "no optimization" as savings.
    """
    text = (text or "").strip()

    if not text:
        return []

    if estimate_tokens(text) <= max_tokens:
        return [text]

    compressed = _normalize_text(text)
    if not compressed:
        compressed = text

    if estimate_tokens(compressed) <= max_tokens:
        return [compressed]

    return _chunk_text(compressed, max_tokens)


def optimized_text_for(text, max_tokens):
    """
    Return the compressed + chunked text (the exact version the AI
    analysis consumes), joined into one readable string.
    Returns None when the text is empty.
    """
    chunks = optimize_for_tokens(text, max_tokens)
    return "\n\n".join(chunks) if chunks else None


def build_optimization_stats(text, max_tokens):
    """
    Compare the source transcript with the optimized (compressed + chunked)
    version and return the optimization block that gets saved in MongoDB.

    Canonical fields:
        original_tokens, optimized_tokens, tokens_saved, reduction_percent,
        original_words, optimized_words, optimization_applied, chunks_created

    tokens_saved      = original_tokens - optimized_tokens
    reduction_percent = ((original_tokens - optimized_tokens) / original_tokens) * 100

    optimization_applied is True ONLY when tokens were actually saved.
    Legacy aliases (cleaned_words, tokens_removed, reduction_percentage,
    estimated_tokens, ...) are kept so older consumers keep working.
    """
    source = text or ""

    original_tokens = estimate_tokens(source)
    original_words = count_words(source)
    original_characters = len(source)

    chunks = optimize_for_tokens(source, max_tokens)
    optimized_text = "\n\n".join(chunks)

    optimized_tokens = estimate_tokens(optimized_text) if chunks else 0
    optimized_words = count_words(optimized_text)
    optimized_characters = len(optimized_text)

    tokens_saved = max(0, original_tokens - optimized_tokens)

    if original_tokens > 0:
        raw_percent = (
            (original_tokens - optimized_tokens) / original_tokens
        ) * 100
        # Chunking joins with a separator which can nudge the estimate up by
        # a fraction, so clamp the display percentage to 0 (never negative).
        reduction_percent = round(max(0.0, raw_percent), 1)
    else:
        reduction_percent = 0.0

    optimization_applied = tokens_saved > 0
    chunks_created = len(chunks)

    # Temporary debug output so savings are easy to verify in the server log.
    print("[OPTIMIZATION] Original tokens: %d" % original_tokens)
    print("[OPTIMIZATION] Optimized tokens: %d" % optimized_tokens)
    print("[OPTIMIZATION] Tokens saved: %d" % tokens_saved)
    print("[OPTIMIZATION] Reduction: %s%%" % reduction_percent)
    print("[OPTIMIZATION] Optimization applied: %s" % str(optimization_applied).lower())
    print("[OPTIMIZATION] Chunks: %d" % chunks_created)

    return {
        # Canonical fields (the frontend uses these).
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": tokens_saved,
        "reduction_percent": reduction_percent,
        "original_words": original_words,
        "optimized_words": optimized_words,
        "optimization_applied": optimization_applied,
        "chunks_created": chunks_created,

        # Legacy aliases so old consumers (dashboard/cards) keep working.
        "cleaned_words": optimized_words,
        "original_characters": original_characters,
        "cleaned_characters": optimized_characters,
        "estimated_tokens": original_tokens,
        "tokens_removed": tokens_saved,
        "reduction_percentage": reduction_percent,
    }