from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
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
    Receives user audio entry. 
    Logic: Checks if an entry for TODAY exists.
    - If YES: Appends new transcript to existing entry. (Single Daily Entry)
    - If NO: Creates new entry.
    """
    try:
        from datetime import datetime, time
        
        # 1. Save File & Transcribe
        file_path = save_audio_file(file)
        result = transcribe_audio(file_path)
        new_transcript = result["text"]
        language = result.get("language", "en")
        
        # 2. Check for existing entry TODAY
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        existing_entry = session.exec(
            select(Entry)
            .where(Entry.user_id == user_id)
            .where(Entry.created_at >= today_start)
            .order_by(Entry.created_at.desc())
        ).first()
        
        if existing_entry:
            # APPEND logic
            print(f"DEBUG: Appending to existing entry {existing_entry.id}", flush=True)
            timestamp = datetime.now().strftime("%H:%M")
            existing_entry.transcript = (existing_entry.transcript or "") + f"\n\n[{timestamp}] {new_transcript}"
            # We keep the old audio_path as primary, or could update it. 
            # For now, we just update transcript as that's what matters for RAG/Briefing.
            
            # Extract Todos from the NEW chunk only
            from services.todo_service import extract_todos_from_transcript
            todo_count = extract_todos_from_transcript(user_id, new_transcript, existing_entry.id, session)
            
            session.add(existing_entry)
            session.commit()
            session.refresh(existing_entry)
            
            return {
                "status": "updated", 
                "entry_id": existing_entry.id, 
                "transcript": existing_entry.transcript, 
                "todos_created": todo_count
            }
            
        else:
            # CREATE logic
            entry = Entry(
                audio_path=file_path, 
                transcript=new_transcript, 
                language=language,
                user_id=user_id
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)

            # Extract Todos
            from services.todo_service import extract_todos_from_transcript
            todo_count = extract_todos_from_transcript(user_id, new_transcript, entry.id, session)
            
            return {
                "status": "created", 
                "entry_id": entry.id, 
                "transcript": new_transcript, 
                "language": language,
                "todos_created": todo_count
            }

    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        if "api_key" in str(e).lower() or "apikey" in str(e).lower():
             raise HTTPException(status_code=500, detail="OpenAI API Key Invalid or Missing.")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


class UpdateEntryRequest(SQLModel):
    transcript: str

@router.put("/{entry_id}")
def update_entry(entry_id: int, request: UpdateEntryRequest, session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Allow editing the transcript text manually."""
    entry = session.get(Entry, entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry.transcript = request.transcript
    session.add(entry)
    session.commit()
    return {"status": "success", "transcript": entry.transcript}
