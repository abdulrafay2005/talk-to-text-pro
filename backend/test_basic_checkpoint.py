import os, sys
from dotenv import load_dotenv

# This file lives in backend/, so the .env is next to it.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("[FAIL] GEMINI_API_KEY not loaded")
    sys.exit(1)
print("[PASS] API key loaded")

client = genai.Client(api_key=API_KEY)
print("[PASS] Gemini client initialized")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

print(f"=== TEST 1: basic generate_content ({MODEL}) ===")
try:
    resp = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly the word OK.",
    )
    print("Response:", repr(getattr(resp, "text", None))[:120])
    print("[PASS] TEST 1 basic Gemini HTTPS")
except Exception as e:
    print(f"[FAIL] TEST 1 basic Gemini HTTPS: {type(e).__name__}: {e}")
    print("Classification: environment/network/TLS problem if this is an SSL EOF")
    raise
