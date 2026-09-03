import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = os.getenv(
    "GEMINI_TRANSCRIPTION_MODEL",
    "gemini-3.5-transcribe"
)

print("Model:", MODEL)
print("Uploading meeting.mp4...")

try:
    uploaded = client.files.upload(
        file="meeting.mp4",
        config=types.UploadFileConfig(
            mime_type="audio/mp4"
        )
    )

    print("UPLOAD SUCCESS")
    print("Name:", uploaded.name)
    print("URI:", uploaded.uri)
    print("Initial state:", uploaded.state)

    print("\nWaiting for Gemini file to become ACTIVE...")

    for i in range(60):
        metadata = client.files.get(name=uploaded.name)

        print(
            f"Check {i + 1}: "
            f"state={metadata.state}, "
            f"mime={metadata.mime_type}"
        )

        state = str(metadata.state).upper()

        if "ACTIVE" in state:
            print("\nFILE IS ACTIVE!")
            break

        if "FAILED" in state:
            raise RuntimeError("Gemini file processing FAILED.")

        time.sleep(2)

    else:
        raise RuntimeError("Timed out waiting for ACTIVE state.")

    print("\nSending transcription request...")

    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "audio",
                "uri": metadata.uri,
                "mime_type": metadata.mime_type,
            }
        ],
        generation_config={
            "transcription_config": {
                "mode": {
                    "type": "smart"
                }
            }
        },
    )

    print("\n========== TRANSCRIPTION SUCCESS ==========")
    print(interaction.output_text)

except Exception as e:
    print("\n========== FAILED ==========")
    print(type(e).__name__)
    print(e)

finally:
    if "uploaded" in locals():
        try:
            client.files.delete(name=uploaded.name)
            print("\nTest file deleted.")
        except Exception as e:
            print("Could not delete test file:", e)