import os
import shutil
from fastapi import UploadFile
from google import genai
from google.genai import types
from config import settings
from uuid import uuid4
import json

# Initialize Gemini Client
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def save_audio_file(file: UploadFile) -> str:
    """
    Saves the uploaded audio file to the configured audio directory.
    Returns the absolute path to the saved file.
    """
    file_id = str(uuid4())
    # Extract extension or default to .webm or .wav
    ext = file.filename.split(".")[-1] if "." in file.filename else "webm"
    filename = f"{file_id}.{ext}"
    
    # Ensure directory exists (defensive programming for Render)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
    
    file_path = os.path.join(settings.AUDIO_DIR, filename)
    print(f"DEBUG: Saving audio to {file_path}") # Log the path
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"CRITICAL: Failed to write file to {file_path}: {e}")
        raise e
        
    return file_path

def transcribe_audio(file_path: str) -> dict:
    """
    Transcribes the audio file using Gemini 2.5 Flash.
    Returns dict with 'text' and 'language'.
    """
    # Verify file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        # Prompt for transcription and language detection
        prompt = (
            "Listen to this audio file. "
            "1. Transcribe the spoken content exactly (in the original language). "
            "2. Detect the language code (e.g. 'de', 'en'). "
            "Output valid JSON only: {\"text\": \"...\", \"language\": \"...\"} "
        )

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type="audio/mp3"  # Generic mime assumption, Gemini is analyzing bytes
                        ),
                        types.Part(text=prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Parse JSON response
        result = json.loads(response.text)
        return {
            "text": result.get("text", ""),
            "language": result.get("language", "en")
        }

    except Exception as e:
        print(f"STT Error (Gemini): {e}")
        # Fallback empty
        return {"text": "", "language": "en"}
