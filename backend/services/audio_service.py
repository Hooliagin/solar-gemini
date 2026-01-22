import os
import shutil
from fastapi import UploadFile
from openai import OpenAI
from config import settings
from uuid import uuid4

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
    Transcribes the audio file using OpenAI Whisper.
    Returns dict with 'text' and 'language'.
    """
    # Verify file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json"  # Get language info
        )
    
    return {
        "text": transcription.text,
        "language": getattr(transcription, 'language', 'en')  # Default to 'en' if not detected
    }
