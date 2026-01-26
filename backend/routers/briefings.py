from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import logging
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
        
    return FileResponse(briefing.audio_path, media_type="audio/wav")

logger = logging.getLogger(__name__)

@router.post("/generate")
async def trigger_briefing_generation(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually triggers the generation of a morning briefing (Async).
    """
    from services.content_generator import generate_briefing_content
    
    def run_generation(uid: str):
        try:
            logger.info(f"Background generation started for user {uid}")
            generate_briefing_content(target_user_id=uid)
            logger.info(f"Background generation finished for user {uid}")
        except Exception as e:
            logger.error(f"Background generation failed: {e}")
            import traceback
            traceback.print_exc()

    try:
        logger.info(f"Queuing briefing generation for user {user_id}")
        background_tasks.add_task(run_generation, user_id)
        return {"status": "success", "message": "Briefing generation started in background"}
    except Exception as e:
        logger.error(f"Failed to queue task: {e}")
        raise HTTPException(status_code=500, detail=f"Queue failed: {str(e)}")
