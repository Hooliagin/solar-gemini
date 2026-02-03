from fastapi import APIRouter, Depends
from sqlmodel import select, Session
from database import get_session
from models import UserSettings, Entry
from services.scheduler import check_reminders, check_briefings
from datetime import datetime
import logging

# Configure logger to capture output for return if possible, 
# but for now we'll just return the data we find.
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])

from auth import get_current_user_id
from models import Briefing, Interest

@router.get("/files")
def inspect_files():
    """
    Lists files in the AUDIO_DIR to verify persistence.
    """
    from config import settings
    import os
    
    try:
        if not os.path.exists(settings.AUDIO_DIR):
             return {"status": "error", "message": f"Directory not found: {settings.AUDIO_DIR}"}
             
        files = os.listdir(settings.AUDIO_DIR)
        return {
            "directory": settings.AUDIO_DIR,
            "absolute_path": os.path.abspath(settings.AUDIO_DIR),
            "file_count": len(files),
            "files": files
        }
    except Exception as e:
         return {"error": str(e)}

@router.get("/me")
def inspect_me(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """
    Returns debug info for the CURRENTLY LOGGED IN user.
    """
    try:
        # User Settings
        user = session.exec(select(UserSettings).where(UserSettings.user_id == user_id)).first()
        
        # Counts
        briefing_count = session.exec(select(Briefing).where(Briefing.user_id == user_id)).all()
        entry_count = session.exec(select(Entry).where(Entry.user_id == user_id)).all()
        
        # Latest Briefing (Raw)
        latest_briefing = session.exec(select(Briefing).where(Briefing.user_id == user_id).order_by(Briefing.created_at.desc()).limit(1)).first()
        
        return {
            "my_user_id": user_id,
            "has_settings": user is not None,
            "telegram_connected": user.telegram_enabled if user else False,
            "telegram_chat_id": user.telegram_chat_id if user else None,
            "total_briefings": len(briefing_count),
            "total_entries": len(entry_count),
            "latest_briefing": latest_briefing
        }
    finally:
        session.close()

@router.get("/users")
def inspect_users():
    session = next(get_session())
    try:
        users = session.exec(select(UserSettings)).all()
        results = []
        for user in users:
            results.append({
                "name": user.name,
                "user_id": user.user_id,
                "telegram_enabled": user.telegram_enabled,
                "chat_id": user.telegram_chat_id,
                "reflection_time": user.reflection_time,
                "reminder_enabled": user.reflection_reminder_enabled,
                "briefing_time": user.briefing_time
            })
        return results
    finally:
        session.close()

@router.post("/trigger-check")
def trigger_check(time_override: str = None):
    """
    Manually trigger checks.
    If time_override is provided (HH:MM), uses that.
    Start with Berlin time logic to match scheduler.
    """
    import pytz
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    current_time = time_override if time_override else now.strftime("%H:%M")
    
    logger.info(f"DEBUG TRIGGER: Checking for time {current_time}")
    
    # We can't easily capture the logs of the checking functions without refactoring.
    # But we can replicate the query logic here to see what WOULD happen.
    
    session = next(get_session())
    report = {
        "checked_time": current_time,
        "server_time_berlin": now.strftime("%H:%M"),
        "reminders_found": [],
        "briefings_found": []
    }
    
    try:
        # Check Reminders Logic
        stmt = select(UserSettings).where(
            UserSettings.telegram_enabled == True,
            UserSettings.telegram_chat_id != None,
            UserSettings.reflection_reminder_enabled == True,
            UserSettings.reflection_time == current_time
        )
        users = session.exec(stmt).all()
        
        for user in users:
            # Check entry
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            entry = session.exec(
                select(Entry).where(
                    Entry.user_id == user.user_id,
                    Entry.created_at >= today_start
                )
            ).first()
            
            report["reminders_found"].append({
                "user": user.name,
                "has_entry_today": entry is not None,
                "would_send": entry is None
            })
            
            # TRIGGER REAL SEND
            # check_reminders(current_time) 
            
    finally:
        session.close()
        
    return report

@router.get("/env")
def inspect_env():
    """
    Checks environment variables debugging (safely).
    """
    from config import settings
    
    url = settings.SUPABASE_URL
    has_key = bool(settings.SUPABASE_KEY)
    
    base_url = url.rstrip('/') if url else None
    derived_jwks_url = f"{base_url}/auth/v1/jwks" if base_url else None
    
    return {
        "SUPABASE_URL_RAW": url,
        "SUPABASE_KEY_SET": has_key,
        "DERIVED_JWKS_URL": derived_jwks_url,
        "AUTH_PY_LOGIC_CHECK": {
            "base_url": base_url,
            "valid_format": "https://<project>.supabase.co" in url if url else False
        }
    }
