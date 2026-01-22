from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlmodel import Session, select
from database import get_session
from models import Entry
from services.audio_service import save_audio_file, transcribe_audio
from auth import get_current_user_id
import logging
from typing import List

router = APIRouter(prefix="/entries", tags=["entries"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Entry])
def get_entries(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Get all diary entries for current user."""
    statement = select(Entry).where(Entry.user_id == user_id).order_by(Entry.created_at.desc())
    return session.exec(statement).all()

@router.post("/upload")
async def upload_entry(file: UploadFile = File(...), session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """
    Receives user audio entry, saves it, transcribes it, and stores it in DB.
    """
    try:
        # 1. Save File
        file_path = save_audio_file(file)
        
        # 2. Transcribe (now returns dict with text and language)
        result = transcribe_audio(file_path)
        transcript = result["text"]
        language = result.get("language", "en")
        
        # 3. Save to DB with user_id
        entry = Entry(
            audio_path=file_path, 
            transcript=transcript, 
            language=language,
            user_id=user_id
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        
        return {"status": "success", "entry_id": entry.id, "transcript": transcript, "language": language}

    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        # Check if it's an OpenAI error or missing key
        if "api_key" in str(e).lower() or "apikey" in str(e).lower():
             raise HTTPException(status_code=500, detail="OpenAI API Key Invalid or Missing.")
        
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
