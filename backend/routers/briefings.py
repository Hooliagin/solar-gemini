from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from database import get_session
from models import Briefing
import os

router = APIRouter(prefix="/briefings", tags=["briefings"])

@router.get("/latest")
async def get_latest_briefing(session: Session = Depends(get_session)):
    """
    Returns the most recent briefing metadata.
    """
    statement = select(Briefing).order_by(Briefing.created_at.desc()).limit(1)
    briefing = session.exec(statement).first()
    
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing found")
    
    return briefing

@router.get("/{briefing_id}/audio")
async def get_briefing_audio(briefing_id: int, session: Session = Depends(get_session)):
    """
    Streams the audio file for a briefing.
    """
    briefing = session.get(Briefing, briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
        
    if not os.path.exists(briefing.audio_path):
        raise HTTPException(status_code=404, detail="Audio file missing")
        
    return FileResponse(briefing.audio_path, media_type="audio/mpeg")
