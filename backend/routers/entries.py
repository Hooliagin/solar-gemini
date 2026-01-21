from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlmodel import Session
from database import get_session
from models import Entry
from services.audio_service import save_audio_file, transcribe_audio
import logging

router = APIRouter(prefix="/entries", tags=["entries"])
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_entry(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Receives user audio entry, saves it, transcribes it, and stores it in DB.
    """
    try:
        # 1. Save File
        file_path = save_audio_file(file)
        
        # 2. Transcribe
        transcript = transcribe_audio(file_path)
        
        # 3. Save to DB
        entry = Entry(audio_path=file_path, transcript=transcript)
        session.add(entry)
        session.commit()
        session.refresh(entry)
        
        return {"status": "success", "entry_id": entry.id, "transcript": transcript}

    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        # Check if it's an OpenAI error or missing key
        if "api_key" in str(e).lower() or "apikey" in str(e).lower():
             raise HTTPException(status_code=500, detail="OpenAI API Key Invalid or Missing.")
        
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
