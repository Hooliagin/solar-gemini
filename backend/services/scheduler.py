"""
Scheduler service for automated briefing generation and reminders.
Since we are on a paid "Always On" plan, this runs internally every minute.
"""
from config import settings
from datetime import datetime
import logging
import asyncio
from sqlmodel import select
from models import UserSettings, Briefing, Entry
from database import get_session
from services.content_generator import generate_briefing_content
from services.telegram_service import send_briefing_audio, send_text_message

logger = logging.getLogger(__name__)

def check_briefings(current_time: str):
    """Check for users due for a briefing now."""
    session = next(get_session())
    try:
        # Find users who want a briefing NOW and have Telegram enabled
        statement = select(UserSettings).where(
            UserSettings.telegram_enabled == True,
            UserSettings.telegram_chat_id != None,
            UserSettings.briefing_time == current_time
        )
        users = session.exec(statement).all()
        
        if not users:
            return

        logger.info(f"Found {len(users)} users due for briefing at {current_time}")
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for user in users:
            # Check if already sent today
            existing = session.exec(
                select(Briefing).where(
                    Briefing.user_id == user.user_id,
                    Briefing.created_at >= today_start
                )
            ).first()
            
            if existing:
                continue
                
            # Generate Background Task
            # We call the async function synchronously here via asyncio.run or similar mechanism if needed, 
            # but better to queue it. For simplicity in this loop, we try/except wrapper.
            try:
                # We need to run async code here. 
                # Since this is likely running in a background thread or APScheduler job:
                asyncio.run(process_briefing(user))
            except Exception as e:
                logger.error(f"Error triggering briefing for {user.user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_briefings: {e}")
    finally:
        session.close()

async def process_briefing(user: UserSettings):
    """Async wrapper to generate and send."""
    briefing = generate_briefing_content(user.user_id)
    if briefing and briefing.audio_path:
        await send_text_message(user.telegram_chat_id, "☀️ **Guten Morgen!**\n\nHier ist dein persönliches Briefing:")
        await send_briefing_audio(user.telegram_chat_id, briefing.audio_path)

def check_reminders(current_time: str):
    """Check for users due for a reflection reminder."""
    session = next(get_session())
    try:
        statement = select(UserSettings).where(
            UserSettings.telegram_enabled == True,
            UserSettings.telegram_chat_id != None,
            UserSettings.reflection_reminder_enabled == True,
            UserSettings.reflection_time == current_time
        )
        users = session.exec(statement).all()
        
        if not users:
            return

        logger.info(f"Checking reminders for {len(users)} users at {current_time}")
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for user in users:
            # Check if they have an entry for today
            entry = session.exec(
                select(Entry).where(
                    Entry.user_id == user.user_id,
                    Entry.created_at >= today_start
                )
            ).first()
            
            if entry:
                # User already journaled, no reminder needed
                continue
            
            # Send Reminder
            try:
                 asyncio.run(send_text_message(
                     user.telegram_chat_id, 
                     f"🌙 **Guten Abend, {user.name or 'Freund'}!**\n\n"
                     "Du hast heute noch keinen Tagebuch-Eintrag gemacht.\n"
                     "Nimm dir doch kurz 2 Minuten für dich.\n\n"
                     "🎤 *Sende einfach eine Sprachnachricht.*"
                 ))
                 logger.info(f"Sent reminder to {user.user_id}")
            except Exception as e:
                logger.error(f"Error sending reminder to {user.user_id}: {e}")
                
    except Exception as e:
         logger.error(f"Error in check_reminders: {e}")
    finally:
        session.close()

def run_scheduler_checks():
    """Called every minute by the main loop."""
    import pytz
    
    # Use Berlin time for all users for now (MVP simplification)
    # Ideally, we store user timezone, but user is explicitly German.
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    current_time = now.strftime("%H:%M")
    
    # Log heartbeat every 15 mins
    if now.minute % 15 == 0:
        logger.info(f"Scheduler tick: {current_time} (Berlin Time)")
        
    check_briefings(current_time)
    check_reminders(current_time)


