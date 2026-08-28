import json
import os
import re
from collections import Counter

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.token_utils import estimate_tokens, optimize_for_tokens

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
MAX_ANALYSIS_TOKENS = int(os.getenv("MAX_ANALYSIS_TOKENS", "1000"))

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT_TEMPLATE = """You are an AI meeting information extractor.

Read the transcript carefully.

Extract only information explicitly stated in the transcript.

Never infer, guess, invent, correct, or add information that is not
supported by the transcript.

Do not change people's names, roles, responsibilities, numbers,
percentages, dates, times, or technical terms.

IMPORTANT DISTINCTIONS:

- A discussion is not a decision.
- An opinion is not a decision.
- A suggestion is not a decision.
- A question is not a decision.
- A disagreement is not a decision.
- A possible future action is not automatically an action item.

Only include something in "decisions" when the transcript clearly
indicates that the group agreed to it, approved it, or someone was
explicitly instructed to do it.

Only include something in "action_items" when the transcript clearly
identifies a person responsible for a task.

Do not invent a person responsible for an action.

Do not create deadlines unless a deadline is explicitly stated.

If a deadline is not stated, use "Not specified".

If responsibility is unclear, do not assign the task to a person.

Preserve uncertainty instead of guessing.

If information is missing, use "Not specified".

Analyze the actual content rather than assuming the meeting type.

Return ONLY valid JSON with this exact structure:

{
    "meeting_type": "...",
    "summary": "...",
    "key_points": ["..."],
    "topics": ["..."],
    "decisions": ["..."],
    "action_items": [
        {
            "person": "...",
            "task": "...",
            "deadline": "..."
        }
    ],
    "unresolved_issues": ["..."],
    "sentiment": "Positive"
}

The sentiment must be one of: Positive, Neutral, Negative.

Transcript:
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

VALID_SENTIMENTS = {"Positive", "Neutral", "Negative"}

ASK_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions about a meeting transcript.

Rules:
- Answer only using information explicitly present in the transcript.
- If the answer is NOT in the transcript, reply exactly:
This information was not mentioned in the meeting.
- Never guess or invent information.
- Keep your answer short and clear.

Transcript:
{transcript}

Question: {question}

Answer:"""

MAX_ASK_TRANSCRIPT_CHARS = 10000


def ask_gemini(prompt, as_json=True):
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

    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text


def clean_answer(raw_text):
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]

    return text.strip()


def answer_question(meeting, question):
    transcript = (
        meeting.get("transcript_cleaned")
        or meeting.get("transcript_raw")
        or ""
    )

    question = (question or "").strip()

    if not question:
        return "Please enter a question."

    prompt = ASK_PROMPT_TEMPLATE.replace(
        "{transcript}", transcript[-MAX_ASK_TRANSCRIPT_CHARS:]
    ).replace(
        "{question}", question
    )

    try:
        answer = clean_answer(ask_gemini(prompt, as_json=False))
        return answer or "This information was not mentioned in the meeting."
    except Exception as e:
        print(f"[GEMINI ASK ERROR] {type(e).__name__}: {e}")
        return "I could not get an answer right now. Please check your Gemini API configuration."


def parse_ai_response(raw_text):
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return json.loads(text)


def complete_missing_fields(result):
    if not isinstance(result, dict):
        return dict(EMPTY_ANALYSIS)

    for key, default in EMPTY_ANALYSIS.items():
        if key not in result:
            result[key] = default

    for key in ["key_points", "topics", "decisions", "unresolved_issues"]:
        if not isinstance(result[key], list):
            result[key] = []

    if not isinstance(result["action_items"], list):
        result["action_items"] = []
    else:
        result["action_items"] = [
            {
                "person": item.get("person") or "Not specified",
                "task": item.get("task") or "Not specified",
                "deadline": item.get("deadline") or "Not specified",
            }
            for item in result["action_items"]
            if isinstance(item, dict)
        ]

    result["summary"] = str(result["summary"] or "Not specified")
    result["meeting_type"] = str(
        result["meeting_type"] or "General Meeting"
    )

    if result.get("sentiment") not in VALID_SENTIMENTS:
        result["sentiment"] = "Neutral"

    return result


def analyze_meeting(transcript):
    transcript = transcript or ""

    if not transcript.strip():
        return complete_missing_fields(dict(EMPTY_ANALYSIS))

    if estimate_tokens(transcript) > MAX_ANALYSIS_TOKENS:
        try:
            chunks = optimize_for_tokens(
                transcript,
                MAX_ANALYSIS_TOKENS
            )

            print(f"[GEMINI] Analyzing {len(chunks)} chunks...")

            results = [
                _analyze_single(chunk)
                for chunk in chunks
            ]

            return combine_results(results)

        except Exception as e:
            print(f"[GEMINI CHUNK ERROR] {type(e).__name__}: {e}")
            return complete_missing_fields(
                empty_analysis_with_error()
            )

    return _analyze_single(transcript)


def _analyze_single(transcript):
    prompt = PROMPT_TEMPLATE.replace(
        "{transcript}", transcript
    )

    try:
        print(f"[GEMINI] Analyzing with {GEMINI_MODEL}...")

        raw_answer = ask_gemini(prompt, as_json=True)
        result = parse_ai_response(raw_answer)

        print("[GEMINI] Analysis complete.")

        return complete_missing_fields(result)

    except Exception as e:
        print(f"[GEMINI ANALYSIS ERROR] {type(e).__name__}: {e}")
        return complete_missing_fields(
            empty_analysis_with_error()
        )


def empty_analysis_with_error():
    result = dict(EMPTY_ANALYSIS)
    result["summary"] = (
        "AI analysis could not be generated. "
        "Please check your Gemini API key, model, and connection."
    )
    return result


def combine_results(results):
    if not results:
        return complete_missing_fields(dict(EMPTY_ANALYSIS))

    combined = dict(EMPTY_ANALYSIS)

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
        meeting_types.append(result["meeting_type"])
        sentiments.append(result["sentiment"])

    combined["summary"] = _join_unique_texts(summaries)
    combined["key_points"] = _dedupe(key_points)
    combined["topics"] = _dedupe(topics)
    combined["decisions"] = _dedupe(decisions)
    combined["action_items"] = _dedupe_dicts(action_items)
    combined["unresolved_issues"] = _dedupe(unresolved)
    combined["meeting_type"] = _most_common(
        meeting_types, "General Meeting"
    )
    combined["sentiment"] = _most_common(
        sentiments, "Neutral"
    )

    return complete_missing_fields(combined)


def _dedupe(items):
    seen = set()
    unique = []

    for item in items:
        normalized = str(item or "").strip().lower()

        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(item)

    return unique


def _dedupe_dicts(items):
    seen = set()
    unique = []

    for item in items:
        key = (
            str(item.get("person", "")).lower().strip(),
            str(item.get("task", "")).lower().strip(),
            str(item.get("deadline", "")).lower().strip(),
        )

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def _join_unique_texts(texts):
    result = []

    for text in texts:
        text = (text or "").strip()

        if text and (not result or result[-1] != text):
            result.append(text)

    return " ".join(result)


def _most_common(values, default):
    if not values:
        return default

    counter = Counter(
        str(value or "").strip()
        for value in values
        if value
    )

    return counter.most_common(1)[0][0] if counter else default