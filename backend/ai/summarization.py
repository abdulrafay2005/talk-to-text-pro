import json
import os
import re
from collections import Counter

from google.genai import types

from ai.gemini_client import (
    get_client,
    request_with_retry,
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ============================================================
# MEETING ANALYSIS PROMPT
# ============================================================

PROMPT_TEMPLATE = """
You are an AI meeting information extractor.

Analyze the meeting transcript below.

IMPORTANT RULES:

1. Use ONLY information explicitly stated in the transcript.
2. Never guess or invent information.
3. Never change names, roles, responsibilities, dates, numbers,
   deadlines, or technical terms.
4. A discussion is NOT automatically a decision.
5. An opinion is NOT automatically a decision.
6. A suggestion is NOT automatically a decision.
7. A question is NOT automatically a decision.
8. Only include decisions when the transcript clearly indicates
   that something was agreed, approved, decided, or instructed.
9. Only create an action item when a responsible person is explicitly
   identified.
10. Never invent a responsible person.
11. Never invent a deadline.
12. If a deadline is not stated, use "Not specified".
13. If information is missing, use "Not specified".
14. Analyze the actual meeting instead of assuming its type.
15. Keep the results concise and useful.

Return ONLY valid JSON.

Use exactly this structure:

{
    "meeting_type": "General Meeting",
    "summary": "Short summary of the meeting.",
    "key_points": [
        "Important point 1",
        "Important point 2"
    ],
    "topics": [
        "Topic 1",
        "Topic 2"
    ],
    "decisions": [
        "Decision 1"
    ],
    "action_items": [
        {
            "person": "Person name",
            "task": "Task",
            "deadline": "Deadline or Not specified"
        }
    ],
    "unresolved_issues": [
        "Unresolved issue"
    ],
    "sentiment": "Neutral"
}

The sentiment MUST be exactly one of:

Positive
Neutral
Negative

TRANSCRIPT:

{transcript}
"""


EMPTY_ANALYSIS = {
    "meeting_type": "General Meeting",
    "summary": "Not specified",
    "key_points": [],
    "topics": [],
    "decisions": [],
    "action_items": [],
    "unresolved_issues": [],
    "sentiment": "Neutral",
}


VALID_SENTIMENTS = {
    "Positive",
    "Neutral",
    "Negative",
}


# ============================================================
# ASK YOUR MEETING
# ============================================================

ASK_PROMPT_TEMPLATE = """
You are a helpful assistant that answers questions about a meeting.

Answer ONLY using information explicitly present in the transcript.

Rules:

- Do not guess.
- Do not invent information.
- Do not use outside knowledge.
- If the answer is not present in the transcript, reply exactly:

This information was not mentioned in the meeting.

Keep the answer short and clear.

TRANSCRIPT:

{transcript}

QUESTION:

{question}

ANSWER:
"""

MAX_ASK_TRANSCRIPT_CHARS = 12000


# ============================================================
# GEMINI REQUEST
# ============================================================

def ask_gemini(prompt, as_json=True):
    """
    Send a prompt to Gemini and return the response text.

    Uses the shared robust request helper (request_with_retry), which
    retries transient TLS / connection errors with a fresh client and
    retries HTTP status errors (429/503/...) via the SDK. Permanent errors
    (bad key/model/request) fail immediately.
    """
    print(f"[GEMINI] Model: {GEMINI_MODEL}")
    print(f"[GEMINI] JSON mode: {as_json}")
    print(f"[GEMINI] Prompt length: {len(prompt)} characters")

    def _do_request():
        client = get_client()

        config = None
        if as_json:
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )

        if response is None:
            raise RuntimeError("Gemini returned no response.")

        text = getattr(response, "text", None)

        if not text:
            raise RuntimeError(
                f"Gemini returned an empty response. Raw response: {response}"
            )

        return text

    text = request_with_retry(
        _do_request,
        description="generate_content",
    )

    print(f"[GEMINI] Response length: {len(text)} characters")

    return text


# ============================================================
# RESPONSE CLEANING
# ============================================================

def clean_answer(raw_text):
    """
    Clean normal Gemini text responses.
    """

    text = (raw_text or "").strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    return text.strip()


def parse_ai_response(raw_text):
    """
    Safely convert Gemini's JSON response into a Python dictionary.
    """

    text = clean_answer(raw_text)

    if not text:
        raise ValueError("Gemini returned empty JSON.")

    # First try normal JSON parsing.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: find the JSON object inside the response.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"Could not find a JSON object in Gemini response: {text[:500]}"
        )

    json_text = text[start:end + 1]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON returned by Gemini: {e}. "
            f"Response: {json_text[:1000]}"
        )


# ============================================================
# NORMALIZE AI RESULT
# ============================================================

def complete_missing_fields(result):
    """
    Make sure the AI result always has the expected structure.
    """

    if not isinstance(result, dict):
        result = {}

    normalized = dict(EMPTY_ANALYSIS)

    normalized.update(result)

    # Strings
    normalized["meeting_type"] = (
        str(normalized.get("meeting_type") or "General Meeting")
        .strip()
    )

    normalized["summary"] = (
        str(normalized.get("summary") or "Not specified")
        .strip()
    )

    # Lists
    for key in [
        "key_points",
        "topics",
        "decisions",
        "unresolved_issues",
    ]:
        value = normalized.get(key)

        if not isinstance(value, list):
            normalized[key] = []
        else:
            normalized[key] = [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

    # Action items
    action_items = normalized.get("action_items")

    if not isinstance(action_items, list):
        action_items = []

    cleaned_action_items = []

    for item in action_items:

        if not isinstance(item, dict):
            continue

        cleaned_action_items.append(
            {
                "person": str(
                    item.get("person") or "Not specified"
                ).strip(),

                "task": str(
                    item.get("task") or "Not specified"
                ).strip(),

                "deadline": str(
                    item.get("deadline") or "Not specified"
                ).strip(),
            }
        )

    normalized["action_items"] = cleaned_action_items

    # Sentiment
    sentiment = normalized.get("sentiment")

    if sentiment not in VALID_SENTIMENTS:
        sentiment = "Neutral"

    normalized["sentiment"] = sentiment

    return normalized


# ============================================================
# MEETING ANALYSIS
# ============================================================

# If a transcript exceeds this many *estimated tokens* (chars / 4) it is
# chunked and each chunk is analyzed separately, then combined. This keeps
# the analysis working for realistic, long meetings without exceeding the
# model context. ~4 chars/token, so 20k chars ~= 5k tokens.
MAX_SINGLE_ANALYSIS_CHARS = int(
    os.getenv("MAX_SINGLE_ANALYSIS_CHARS", "20000")
)


def _chunk_transcript(transcript, max_chars=MAX_SINGLE_ANALYSIS_CHARS):
    """
    Split a transcript into ordered chunks that each fit within max_chars.
    Splits on paragraph, then sentence boundaries; never drops content.
    """
    text = (transcript or "").strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        candidate = remaining[:max_chars]

        # Prefer paragraph breaks.
        pos = candidate.rfind("\n\n")

        # Then sentence endings.
        if pos < max_chars * 0.5:
            pos = max(
                candidate.rfind(". "),
                candidate.rfind("? "),
                candidate.rfind("! "),
            )

        # Last resort: split exactly at max_chars.
        if pos < max_chars * 0.5:
            pos = max_chars

        chunk = remaining[:pos].strip()
        if chunk:
            chunks.append(chunk)

        remaining = remaining[pos:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def analyze_meeting(transcript):
    """
    Analyze the meeting transcript using Gemini.

    Small transcripts are analyzed in one call. Large transcripts are split
    into chunks, each analyzed separately, and the results combined so no
    part of a long meeting is lost.

    Returns a normalized meeting intelligence dictionary.
    """

    transcript = (transcript or "").strip()

    if not transcript:
        print("[GEMINI] Empty transcript. Skipping analysis.")
        return complete_missing_fields({})

    print(
        f"[GEMINI] Starting meeting analysis. "
        f"Transcript chars={len(transcript)}"
    )

    # ---- Large transcript: chunk + analyze each + combine ----
    if len(transcript) > MAX_SINGLE_ANALYSIS_CHARS:

        chunks = _chunk_transcript(transcript, MAX_SINGLE_ANALYSIS_CHARS)
        print(
            f"[GEMINI] Transcript is large "
            f"({len(transcript)} chars). Splitting into "
            f"{len(chunks)} chunks for analysis."
        )

        partial_results = []

        for index, chunk in enumerate(chunks, start=1):
            print(
                f"[GEMINI] Analyzing chunk {index}/{len(chunks)} "
                f"({len(chunk)} chars)..."
            )

            prompt = PROMPT_TEMPLATE.replace(
                "{transcript}",
                chunk,
            )

            try:
                raw_response = ask_gemini(prompt, as_json=True)
                result = parse_ai_response(raw_response)
                result = complete_missing_fields(result)
                partial_results.append(result)
            except Exception as e:
                print(
                    f"[GEMINI] Chunk {index} analysis failed: "
                    f"{type(e).__name__}: {e}"
                )

        if partial_results:
            combined = combine_results(partial_results)
            print("[GEMINI] Combined chunked analysis.")
            return combined

        print("[GEMINI] All chunks failed. Returning empty fallback.")
        return complete_missing_fields({})

    # ---- Normal single-call analysis ----
    prompt = PROMPT_TEMPLATE.replace(
        "{transcript}",
        transcript,
    )

    try:
        raw_response = ask_gemini(
            prompt,
            as_json=True,
        )

        print("[GEMINI] Raw analysis received.")

        result = parse_ai_response(raw_response)

        result = complete_missing_fields(result)

        print("[GEMINI] Analysis successfully parsed.")
        print(
            f"[GEMINI] Meeting type: {result['meeting_type']}"
        )
        print(
            f"[GEMINI] Sentiment: {result['sentiment']}"
        )
        print(
            f"[GEMINI] Key points: {len(result['key_points'])}"
        )
        print(
            f"[GEMINI] Decisions: {len(result['decisions'])}"
        )
        print(
            f"[GEMINI] Action items: {len(result['action_items'])}"
        )

        return result

    except Exception as e:

        # IMPORTANT:
        # Do not hide the real Gemini error.
        print(
            f"[GEMINI ANALYSIS ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return empty_analysis_with_error(
            error=e
        )


# ============================================================
# ANALYSIS ERROR
# ============================================================

def empty_analysis_with_error(error=None):
    """
    Return a safe fallback while preserving the real error
    in the backend terminal.
    """

    result = dict(EMPTY_ANALYSIS)

    if error:
        result["summary"] = (
            "AI analysis failed. "
            "Check the backend terminal for the exact Gemini error."
        )
    else:
        result["summary"] = (
            "AI analysis could not be generated."
        )

    return result


# ============================================================
# ASK YOUR MEETING
# ============================================================

def answer_question(meeting, question):
    """
    Answer a question using the meeting transcript.
    """

    transcript = (
        meeting.get("transcript_cleaned")
        or meeting.get("transcript_raw")
        or ""
    )

    question = (question or "").strip()

    if not question:
        return "Please enter a question."

    # Keep the prompt within a reasonable size.
    transcript = transcript[:MAX_ASK_TRANSCRIPT_CHARS]

    prompt = ASK_PROMPT_TEMPLATE.replace(
        "{transcript}",
        transcript,
    ).replace(
        "{question}",
        question,
    )

    try:

        answer = ask_gemini(
            prompt,
            as_json=False,
        )

        answer = clean_answer(answer)

        if not answer:
            return (
                "This information was not mentioned in the meeting."
            )

        return answer

    except Exception as e:

        print(
            f"[GEMINI ASK ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return (
            "I could not get an answer right now. "
            "Please check the backend terminal."
        )


# ============================================================
# OPTIONAL HELPERS
# ============================================================

def _dedupe(items):
    """
    Remove duplicate text items while preserving order.
    """

    seen = set()
    unique = []

    for item in items:

        text = str(item or "").strip()

        normalized = text.lower()

        if text and normalized not in seen:
            seen.add(normalized)
            unique.append(text)

    return unique


def _dedupe_dicts(items):
    """
    Remove duplicate action items.
    """

    seen = set()
    unique = []

    for item in items:

        if not isinstance(item, dict):
            continue

        key = (
            str(item.get("person", "")).strip().lower(),
            str(item.get("task", "")).strip().lower(),
            str(item.get("deadline", "")).strip().lower(),
        )

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def _join_unique_texts(texts):
    """
    Combine unique summaries.
    """

    unique = _dedupe(texts)

    return " ".join(unique)


def _most_common(values, default):
    """
    Return the most common value.
    """

    if not values:
        return default

    counter = Counter(
        str(value).strip()
        for value in values
        if value
    )

    if not counter:
        return default

    return counter.most_common(1)[0][0]


def combine_results(results):
    """
    Combine multiple analysis results if chunked analysis
    is ever needed later.
    """

    if not results:
        return complete_missing_fields({})

    summaries = []
    key_points = []
    topics = []
    decisions = []
    action_items = []
    unresolved = []
    meeting_types = []
    sentiments = []

    for result in results:

        result = complete_missing_fields(result)

        summaries.append(result["summary"])
        key_points.extend(result["key_points"])
        topics.extend(result["topics"])
        decisions.extend(result["decisions"])
        action_items.extend(result["action_items"])
        unresolved.extend(result["unresolved_issues"])

        meeting_types.append(
            result["meeting_type"]
        )

        sentiments.append(
            result["sentiment"]
        )

    combined = {
        "meeting_type": _most_common(
            meeting_types,
            "General Meeting",
        ),

        "summary": _join_unique_texts(
            summaries
        ),

        "key_points": _dedupe(
            key_points
        ),

        "topics": _dedupe(
            topics
        ),

        "decisions": _dedupe(
            decisions
        ),

        "action_items": _dedupe_dicts(
            action_items
        ),

        "unresolved_issues": _dedupe(
            unresolved
        ),

        "sentiment": _most_common(
            sentiments,
            "Neutral",
        ),
    }

    return complete_missing_fields(combined)