import time
from deep_translator import GoogleTranslator


# Cached translator objects by target language.
_translators = {}

# Stay safely below Google's 5000-character limit.
MAX_CHARS = 3500

# Number of times to retry a failed translation request.
MAX_RETRIES = 3


def get_translator(target_language):
    """
    Return a cached GoogleTranslator for the target language.
    """

    if target_language not in _translators:
        _translators[target_language] = GoogleTranslator(
            source="auto",
            target=target_language
        )

    return _translators[target_language]


def split_text(text, max_chars=MAX_CHARS):
    """
    Split long text into safe-sized chunks.

    Tries to split at paragraph, newline, or sentence boundaries
    instead of cutting sentences whenever possible.
    """

    text = text.strip()

    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:

        candidate = remaining[:max_chars]

        # Prefer paragraph breaks.
        position = candidate.rfind("\n\n")

        # Then normal line breaks.
        if position < max_chars * 0.5:
            position = candidate.rfind("\n")

        # Then sentence endings.
        if position < max_chars * 0.5:
            positions = [
                candidate.rfind(". "),
                candidate.rfind("? "),
                candidate.rfind("! "),
            ]

            position = max(positions)

        # Last resort: split exactly at max_chars.
        if position < max_chars * 0.5:
            position = max_chars

        chunk = remaining[:position].strip()

        if chunk:
            chunks.append(chunk)

        remaining = remaining[position:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def translate_chunk(translator, chunk):
    """
    Translate one chunk with retries.
    """

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:
            result = translator.translate(chunk)

            if result:
                return result

        except Exception as error:
            last_error = error

            print(
                f"Translation attempt {attempt + 1}/"
                f"{MAX_RETRIES} failed: {error}"
            )

            # Wait before retrying.
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)

    # If all retries fail, raise the original error.
    raise last_error


def translate_text(text, target_language):
    """
    Translate the complete transcript into the target language.

    Long transcripts are automatically split into safe chunks.
    Every chunk is translated and then combined.

    The original transcript is never intentionally truncated.
    """

    if not text or not text.strip():
        return ""

    translator = get_translator(target_language)

    chunks = split_text(text)

    print(
        f"Translation started: {len(text)} characters, "
        f"{len(chunks)} chunks"
    )

    translated_chunks = []

    for index, chunk in enumerate(chunks, start=1):

        print(
            f"Translating chunk {index}/{len(chunks)} "
            f"({len(chunk)} characters)..."
        )

        translated = translate_chunk(
            translator,
            chunk
        )

        translated_chunks.append(translated)

        # Small delay between requests to reduce the chance
        # of Google temporarily rejecting requests.
        if index < len(chunks):
            time.sleep(0.5)

    result = "\n\n".join(translated_chunks)

    print(
        f"Translation completed: "
        f"{len(translated_chunks)} chunks"
    )

    return result
