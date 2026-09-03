import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API key loaded:", bool(api_key))

client = genai.Client(api_key=api_key)

test_file = "meeting.mp4"

if not os.path.exists(test_file):
    print(f"ERROR: {test_file} not found")
    print("Put a small MP3 file in the backend folder and run this again.")
    exit()

print("Uploading:", test_file)

try:
    uploaded = client.files.upload(
        file=test_file,
        config=types.UploadFileConfig(
            mime_type="audio/mpeg"
        )
    )

    print("UPLOAD SUCCESS!")
    print("Name:", uploaded.name)
    print("URI:", uploaded.uri)

except Exception as e:
    print("UPLOAD FAILED!")
    print(type(e).__name__)
    print(e)