from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import logging
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from database import get_session
from models import Briefing, UserSettings, BriefingUsage
from auth import get_current_user_id
from services.notification_service import deliver_briefing_notification
import os
from datetime import datetime

DAILY_LIMIT = 50
WEEKLY_LIMIT = 10

def get_or_create_usage(session: Session, user_id: str) -> BriefingUsage:
    """Get or create the BriefingUsage row for the current month."""
    current_month = datetime.utcnow().strftime("%Y-%m")
    usage = session.exec(
        select(BriefingUsage).where(
            BriefingUsage.user_id == user_id,
            BriefingUsage.month == current_month
        )
    ).first()
    if not usage:
        usage = BriefingUsage(user_id=user_id, month=current_month)
        session.add(usage)
        session.commit()
        session.refresh(usage)
    return usage

router = APIRouter(prefix="/briefings", tags=["briefings"])
logger = logging.getLogger(__name__)

@router.get("/usage")
async def get_briefing_usage(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """Returns the current month's briefing usage for the user."""
    usage = get_or_create_usage(session, user_id)
    return {
        "daily_used": usage.daily_count,
        "daily_limit": DAILY_LIMIT,
        "weekly_used": usage.weekly_count,
        "weekly_limit": WEEKLY_LIMIT,
        "month": usage.month
    }

@router.get("/latest")
async def get_latest_briefing(
    type: str = "daily",  # Query parameter, default daily
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Returns the most recent briefing metadata for the current user.
    """
    logger.info(f"Fetching latest {type} briefing for user {user_id}")
    statement = select(Briefing).where(
        Briefing.user_id == user_id, 
        Briefing.type == type
    ).order_by(Briefing.created_at.desc()).limit(1)
    briefing = session.exec(statement).first()
    
    if not briefing:
        logger.warning(f"No briefing found for user {user_id}")
        raise HTTPException(status_code=404, detail="No briefing found")
    
    logger.info(f"Found briefing {briefing.id} for user {user_id}")
    
    # Fetch latest quote for this user to display on Dashboard
    from models import UsedQuote
    quote_stmt = select(UsedQuote).where(UsedQuote.user_id == user_id).order_by(UsedQuote.used_at.desc()).limit(1)
    latest_quote = session.exec(quote_stmt).first()
    
    response_data = briefing.model_dump()
    if latest_quote:
        response_data["quote"] = latest_quote.quote_text_snippet
    else:
        response_data["quote"] = "Wissen ist der Zinseszins der Neugier." # Fallback

    return response_data

@router.get("/{briefing_id}/audio")
async def get_briefing_audio(
    briefing_id: int, 
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Streams the audio file for a briefing.
    """
    briefing = session.get(Briefing, briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
        
    # Security Check: Ensure ownership
    if briefing.user_id != user_id:
        logger.error(f"Access Denied: Briefing Owner '{briefing.user_id}' vs Request User '{user_id}'")
        raise HTTPException(status_code=403, detail="Not authorized to access this briefing")
        
    # Determine if it's a local file (legacy) or Supabase Storage path
    is_storage_path = briefing.audio_path and "/" in briefing.audio_path and not briefing.audio_path.startswith("/")
    
    if is_storage_path:
        # Generate Signed URL
        from services.storage_service import create_signed_url
        try:
             # Validity: 60 seconds (Client should start playing immediately)
             signed_url = create_signed_url(briefing.audio_path, expires_in=60)
             
             # Extract string if it's a dict (supabase-py variation)
             if isinstance(signed_url, dict):
                 signed_url = signed_url.get("signedURL")
             
             # Redirect the client to the Supabase URL
             from fastapi.responses import RedirectResponse
             return RedirectResponse(url=signed_url, status_code=307)
             
        except Exception as e:
            logger.error(f"Failed to sign URL: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve audio file")

    # Fallback for Legacy Local Files
    if not os.path.exists(briefing.audio_path):
        logger.error(f"Audio file missing at path: {briefing.audio_path}")
        raise HTTPException(status_code=404, detail="Audio file missing")
        
    return FileResponse(briefing.audio_path, media_type="audio/wav")



@router.post("/generate")
async def trigger_briefing_generation(
    type: str = "daily",
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually triggers the generation of a morning briefing (Async).
    Type: "daily" or "weekly"
    Enforces monthly limits: 50 daily, 10 weekly.
    """
    if background_tasks is None:
         raise HTTPException(status_code=500, detail="BackgroundTasks not injected properly")

    # --- LIMIT CHECK ---
    usage = get_or_create_usage(session, user_id)
    if type == "daily" and usage.daily_count >= DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Monatliches Limit erreicht: {DAILY_LIMIT} tägliche Briefings pro Monat."
        )
    if type == "weekly" and usage.weekly_count >= WEEKLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Monatliches Limit erreicht: {WEEKLY_LIMIT} wöchentliche Briefings pro Monat."
        )

    from services.content_generator import generate_briefing_content
    
    def run_generation(uid: str, b_type: str):
        from database import get_session as get_bg_session
        bg_session = next(get_bg_session())
        try:
            logger.info(f"Background generation started for user {uid} (Type: {b_type})")
            briefing = generate_briefing_content(target_user_id=uid, briefing_type=b_type)
            
            if briefing:
                # Increment usage counter ONLY on success
                bg_usage = get_or_create_usage(bg_session, uid)
                if b_type == "weekly":
                    bg_usage.weekly_count += 1
                else:
                    bg_usage.daily_count += 1
                bg_session.add(bg_usage)
                bg_session.commit()
                logger.info(f"Usage incremented for {uid}: {b_type} ({bg_usage.daily_count}/50)")
            else:
                logger.error(f"Manual briefing generation failed for {uid}, NOT incrementing usage.")

            if briefing and briefing.audio_path:
                settings_stmt = select(UserSettings).where(UserSettings.user_id == uid)
                user_settings = bg_session.exec(settings_stmt).first()
                
                if user_settings and user_settings.telegram_enabled and user_settings.telegram_chat_id:
                    import asyncio
                    asyncio.run(deliver_briefing_notification(user_settings, briefing))
                    logger.info(f"Manual briefing sent to Telegram for {uid}")

            logger.info(f"Background generation finished for user {uid}")
        except Exception as e:
            logger.error(f"Background generation failed: {e}")
            print(f"DEBUG: BACKGROUND TASK FAILED: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            bg_session.close()

    try:
        logger.info(f"Queuing {type} briefing generation for user {user_id}")
        background_tasks.add_task(run_generation, user_id, type)
        return {"status": "success", "message": "Briefing generation started in background"}
    except Exception as e:
        logger.error(f"Failed to queue task: {e}")
        raise HTTPException(status_code=500, detail=f"Queue failed: {str(e)}")

@router.put("/{briefing_id}/events")
async def update_briefing_events(
    briefing_id: int,
    events: list[dict],
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Updates the cached calendar events for a specific briefing (Manual overrides).
    """
    briefing = session.get(Briefing, briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
        
    if briefing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    import json
    briefing.calendar_events = json.dumps(events)
    session.add(briefing)
    session.commit()
    
    return {"status": "success", "message": "Events updated"}

@router.post("/{briefing_id}/export-calendar")
async def export_briefing_to_calendar(
    briefing_id: int,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    """
    Exports AI-suggested events from the briefing to the user's primary Google Calendar.
    Skips existing events (type='fixed').
    """
    briefing = session.get(Briefing, briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
        
    if briefing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if not briefing.calendar_events:
        return {"status": "ignored", "message": "No events in briefing to export"}
        
    try:
        import json
        from services.calendar_service import create_calendar_event
        
        events = json.loads(briefing.calendar_events)
        exported_count = 0
        failed_count = 0
        
        for event in events:
            # Only export suggestions, ignore fixed original events
            if event.get('type') == 'suggestion' or event.get('calendar') == 'AI Suggestion':
                 # Prepare simple description
                 event_data = {
                     'name': event['name'],
                     'start': event['start'],
                     'end': event.get('end'),
                     'description': "AI Suggestion from Daily Manager"
                 }
                 
                 # If no end time, assume 30m default or parse from string if possible?
                 # Data model guarantees end time usually, but if missing, handle it:
                 if not event_data['end']:
                      # Fallback logic if needed, but assuming valid ISO for now.
                      # Actually, if 'end' is missing, Google API might complain.
                      # Let's try to parse start and add 30 mins if needed.
                      from datetime import datetime, timedelta
                      try:
                          dt = datetime.fromisoformat(event_data['start'])
                          dt_end = dt + timedelta(minutes=30)
                          event_data['end'] = dt_end.isoformat()
                      except:
                          pass

                 success = create_calendar_event(user_id, event_data)
                 if success:
                     exported_count += 1
                 else:
                     failed_count += 1
        
        return {
            "status": "success", 
            "exported": exported_count, 
            "failed": failed_count,
            "message": f"Exported {exported_count} events to your calendar."
        }
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
