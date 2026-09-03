import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for attempt in range(1, 6):
    print(f"\n========== ATTEMPT {attempt} ==========")

    try:
        uploaded = client.files.upload(
            file="meeting.mp4",
            config=types.UploadFileConfig(
                mime_type="audio/mp4"
            )
        )

        print("SUCCESS!")
        print("Name:", uploaded.name)
        print("URI:", uploaded.uri)

        try:
            client.files.delete(name=uploaded.name)
            print("Deleted test upload.")
        except Exception as e:
            print("Delete failed:", e)

    except Exception as e:
        print("FAILED!")
        print(type(e).__name__)
        print(e)

    time.sleep(3)