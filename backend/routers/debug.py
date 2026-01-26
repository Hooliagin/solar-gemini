from fastapi import APIRouter, Depends
from sqlmodel import select
from database import get_session
from models import UserSettings, Entry
from services.scheduler import check_reminders, check_briefings
from datetime import datetime
import logging

# Configure logger to capture output for return if possible, 
# but for now we'll just return the data we find.
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])

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
