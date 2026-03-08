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
from services.notification_service import deliver_briefing_notification
from services.telegram_service import send_text_message


def get_users_due_for_briefing():
    """Helper function for debug endpoint - returns users due for briefing at current time."""
    import pytz
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    current_time = now.strftime("%H:%M")
    
    session = next(get_session())
    try:
        statement = select(UserSettings).where(
            UserSettings.telegram_enabled == True,
            UserSettings.telegram_chat_id != None,
            UserSettings.briefing_time == current_time
        )
        return session.exec(statement).all()
    finally:
        session.close()

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
            
            # Check monthly limit
            from models import BriefingUsage
            current_month = datetime.now().strftime("%Y-%m")
            usage = session.exec(
                select(BriefingUsage).where(
                    BriefingUsage.user_id == user.user_id,
                    BriefingUsage.month == current_month
                )
            ).first()
            if usage and usage.daily_count >= 50:
                logger.info(f"Skipping user {user.user_id} - Monthly daily limit reached ({usage.daily_count}/50).")
                continue
                
            # Generate Background Task
            try:
                # We call the async function synchronously here
                asyncio.run(process_briefing(user))
                
                # Increment usage after successful generation
                if not usage:
                    usage = BriefingUsage(user_id=user.user_id, month=current_month, daily_count=1)
                    session.add(usage)
                else:
                    usage.daily_count += 1
                    session.add(usage)
                session.commit()
                
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


async def process_briefing(user) -> bool:
    """
    Orchestrates the generation and sending of a briefing for a single user.
    Returns True on success, False otherwise.
    """
    try:
        logger.info(f"Processing briefing for user {user.user_id}")
        
        # 1. Generate Content (Sync function, run in threadpool)
        # We wrap it in to_thread to avoid blocking the async event loop
        briefing = await asyncio.to_thread(generate_briefing_content, user.user_id)
        
        if not briefing:
            logger.error(f"Failed to generate briefing content for {user.user_id}")
            return False
            
        # 2. Deliver Notification (Unifies Daily/Weekly + Image generation)
        if user.telegram_enabled and user.telegram_chat_id:
            await deliver_briefing_notification(user, briefing)
            logger.info(f"Briefing sent to Telegram for {user.user_id}")
            return True
        
        # If telegram is not enabled or chat_id is missing, we consider it not "sent"
        logger.warning(f"Briefing not delivered for {user.user_id}: Telegram not enabled or chat_id missing.")
        return False
            
    except Exception as e:
        logger.error(f"Error in process_briefing for {user.user_id}: {e}")
        return False
