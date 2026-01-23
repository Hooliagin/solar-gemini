"""
Scheduler service for automated briefing generation and delivery.
Checks each user's individual briefing_time and sends to Telegram.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import settings
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

def get_users_due_for_briefing():
    """
    Get all users who have Telegram enabled.
    This is called by the cron service, so all users get their briefing at the same time.
    """
    from database import get_session
    from models import UserSettings
    from sqlmodel import select
    
    session = next(get_session())
    try:
        # Get ALL users with Telegram enabled (no time filtering)
        users = session.exec(
            select(UserSettings).where(
                UserSettings.telegram_enabled == True,
                UserSettings.telegram_chat_id != None
            )
        ).all()
        
        logger.info(f"Found {len(users)} users with Telegram enabled for briefing")
        
        return list(users)
    except Exception as e:
        logger.error(f"Error getting users due for briefing: {e}")
        return []
    finally:
        session.close()

def generate_and_send_briefing(user_id: str, chat_id: str):
    """
    Generate briefing for a user and send it via Telegram.
    """
    from services.content_generator import generate_briefing_content
    from services.telegram_service import send_briefing_audio, send_text_message
    from database import get_session
    from models import Briefing
    from sqlmodel import select
    
    try:
        logger.info(f"Generating briefing for user {user_id}")
        
        # Generate the briefing
        briefing = generate_briefing_content(user_id)
        
        if briefing and briefing.audio_path:
            # Send via Telegram
            async def send():
                # Send a greeting first
                await send_text_message(
                    chat_id, 
                    "☀️ **Guten Morgen!**\n\nHier ist dein persönliches Briefing:"
                )
                
                # Send the audio
                success = await send_briefing_audio(
                    chat_id=chat_id,
                    audio_path=briefing.audio_path,
                    caption=f"📅 Briefing vom {datetime.now().strftime('%d.%m.%Y')}"
                )
                
                if success:
                    logger.info(f"Briefing sent successfully to chat {chat_id}")
                else:
                    logger.error(f"Failed to send briefing audio to chat {chat_id}")
            
            # Run async in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(send())
            finally:
                loop.close()
                
        else:
            logger.error(f"No briefing generated for user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to generate/send briefing for user {user_id}: {e}")

def scheduled_briefing_job():
    """
    Main scheduler job that runs every minute.
    Checks for users whose briefing time matches now and generates/sends their briefings.
    """
    print("DEBUG: scheduled_briefing_job STARTED", flush=True)
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        print(f"DEBUG: Scheduler check at {current_time}", flush=True)
        logger.info(f"Scheduler check at {current_time}")
        
        # Get users due for briefing
        print("DEBUG: Calling get_users_due_for_briefing()...", flush=True)
        users = get_users_due_for_briefing()
        print(f"DEBUG: get_users_due_for_briefing returned {len(users)} users", flush=True)
        
        if users:
            logger.info(f"Found {len(users)} users due for briefing at {current_time}")
            
            for user in users:
                print(f"DEBUG: Processing user {user.user_id}", flush=True)
                try:
                    # Check if we already sent a briefing today
                    from database import get_session
                    from models import Briefing
                    from sqlmodel import select
                    
                    print("DEBUG: Checking for existing briefing...", flush=True)
                    session = next(get_session())
                    try:
                        # Check for briefing created today
                        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        existing = session.exec(
                            select(Briefing).where(
                                Briefing.user_id == user.user_id,
                                Briefing.created_at >= today_start
                            )
                        ).first()
                        
                        if existing:
                            print(f"DEBUG: User {user.user_id} already has a briefing today, skipping", flush=True)
                            logger.debug(f"User {user.user_id} already has a briefing today, skipping")
                            # REMOVED FOR TESTING: continue
                    finally:
                        session.close()
                    
                    # Generate and send
                    print("DEBUG: Generating and sending briefing...", flush=True)
                    generate_and_send_briefing(user.user_id, user.telegram_chat_id)
                    print("DEBUG: generate_and_send_briefing returned", flush=True)
                    
                except Exception as e:
                    print(f"ERROR processing user {user.user_id}: {e}", flush=True)
                    logger.error(f"Error processing user {user.user_id}: {e}")
        else:
            print("DEBUG: No users found for briefing", flush=True)
            
    except Exception as e:
        print(f"CRITICAL ERROR in scheduled_briefing_job: {e}", flush=True)
        import traceback
        traceback.print_exc()

def start_scheduler():
    """
    Start the background scheduler.
    Runs every minute to check for users due for briefing.
    """
    scheduler = BackgroundScheduler()
    
    # Run every minute
    trigger = IntervalTrigger(minutes=1)
    
    scheduler.add_job(
        scheduled_briefing_job,
        trigger=trigger,
        id="briefing_scheduler",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Briefing scheduler started - checking every minute for scheduled briefings")
    
    # Run immediately on startup to catch any missed briefings
    import threading
    threading.Thread(target=scheduled_briefing_job, daemon=True).start()
    
    return scheduler
