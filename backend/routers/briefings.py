from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from database import get_session
from models import Briefing
from auth import get_current_user_id
import os

router = APIRouter(prefix="/briefings", tags=["briefings"])

@router.get("/latest")
async def get_latest_briefing(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Returns the most recent briefing metadata for the current user.
    """
    statement = select(Briefing).where(Briefing.user_id == user_id).order_by(Briefing.created_at.desc()).limit(1)
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
        
    if not os.path.exists(briefing.audio_path):
        raise HTTPException(status_code=404, detail="Audio file missing")
        
    return FileResponse(briefing.audio_path, media_type="audio/mpeg")

@router.post("/generate")
async def trigger_briefing_generation(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually triggers the generation of a morning briefing.
    Useful for testing or on-demand updates.
    """
    from services.content_generator import generate_briefing_content
    try:
        # We need to pass the current user_id.
        return {"status": "error", "message": "Endpoint logic incomplete, fixing..."}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
