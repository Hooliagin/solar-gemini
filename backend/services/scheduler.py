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

def run_scheduler_checks():
    """
    Called every minute by the main loop.
    Protected by a distributed lock (Postgres Advisory Lock) to ensure
    only ONE worker executes this logic per minute.
    """
    import pytz
    from sqlalchemy import text
    
    # Use Berlin time for all users
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    current_time = now.strftime("%H:%M")
    
    # Log heartbeat every 15 mins (from ALL workers, to show liveness)
    if now.minute % 15 == 0:
        logger.info(f"Scheduler tick: {current_time} (Worker active)")

    session = next(get_session())
    try:
        # --- DISTRIBUTED LOCKING START ---
        # Try to acquire a transaction-level advisory lock on a specific ID (e.g. 12345)
        # If we get it, we are the LEADER for this minute.
        # If not, we skip immediately.
        # pg_try_advisory_xact_lock automatically releases at end of transaction (commit/close).
        lock_id = 998877 # Arbitrary constant ID for "Morning Briefing Scheduler"
        
        # Execute raw SQL
        result = session.exec(text(f"SELECT pg_try_advisory_xact_lock({lock_id})")).first()
        
        # Result is (True,) or (False,)
        lock_acquired = result[0] if result else False
        
        if not lock_acquired:
            # Another worker is already handling this minute. We yield.
            # logger.debug("Lock not acquired, skipping.")
            session.rollback() # Release potential resources
            return

        logger.info(f"🔒 Lock acquired. I am the leader for {current_time}. Running checks...")
        
        # 1. Briefings
        check_briefings(session, current_time)
        
        # 2. Reminders
        check_reminders(session, current_time)
        
        logger.info("Checks completed. Releasing lock (via commit).")
        session.commit() # This releases the xact lock
        
    except Exception as e:
        logger.error(f"Scheduler Error: {e}")
        session.rollback()
    finally:
        session.close()


def check_briefings(session, current_time: str):
    """Check for users due for a briefing now."""
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
            # Check if already sent today (DEDUPLICATION)
            existing = session.exec(
                select(Briefing).where(
                    Briefing.user_id == user.user_id,
                    Briefing.created_at >= today_start
                )
            ).first()
            
            if existing:
                logger.info(f"Skipping user {user.user_id} - Briefing already sent today.")
                continue
                
            # Generate Background Task
            try:
                # We call the async function synchronously here
                asyncio.run(process_briefing(user))
            except Exception as e:
                logger.error(f"Error triggering briefing for {user.user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_briefings: {e}")


def check_reminders(session, current_time: str):
    """Check for users due for a reflection reminder."""
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




async def process_briefing(user):
    """
    Orchestrates the generation and sending of a briefing for a single user.
    """
    try:
        logger.info(f"Processing briefing for user {user.user_id}")
        
        # 1. Generate Content (Sync function, run in threadpool)
        # We wrap it in to_thread to avoid blocking the async event loop
        briefing = await asyncio.to_thread(generate_briefing_content, user.user_id)
        
        if not briefing:
            logger.error(f"Failed to generate briefing for {user.user_id}")
            return
            
        # 2. Send to Telegram (if enabled)
        if user.telegram_enabled and user.telegram_chat_id:
            caption = f"🌅 Dein Morgen-Briefing für {datetime.now().strftime('%d.%m.%Y')}"
            
            await send_text_message(
                chat_id=user.telegram_chat_id, 
                text=f"🚀 **Guten Morgen, {user.name or 'Freund'}!**\nDein Briefing ist bereit."
            )
            
            await send_briefing_audio(
                chat_id=user.telegram_chat_id,
                audio_path=briefing.audio_path,
                caption=caption
            )
            logger.info(f"Briefing sent to Telegram for {user.user_id}")
            
    except Exception as e:
        logger.error(f"Error in process_briefing for {user.user_id}: {e}")
