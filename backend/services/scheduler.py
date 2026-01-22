from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
import logging

logger = logging.getLogger(__name__)

def generate_morning_briefing_job():
    """
    This function will be called by the scheduler.
    It triggers the briefing generation process.
    """
    logger.info("Starting morning briefing generation job...")
    from services.content_generator import generate_briefing_content
    from database import get_session
    from models import UserSettings
    from sqlmodel import select
    
    session = next(get_session())
    try:
        # Get all users with enabled settings (or just all users)
        # For now, let's just get all users who successfully set up the app.
        users = session.exec(select(UserSettings)).all()
        
        logger.info(f"Found {len(users)} users for briefing generation.")
        
        for user in users:
            try:
                generate_briefing_content(user.user_id)
            except Exception as e:
                logger.error(f"Failed to generate briefing for user {user.user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Scheduler job failed: {e}")
    finally:
        session.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Schedule the job to run every day at the configured time
    trigger = CronTrigger(hour=settings.BRIEFING_TIME_HOUR, minute=settings.BRIEFING_TIME_MINUTE)
    
    scheduler.add_job(
        generate_morning_briefing_job,
        trigger=trigger,
        id="morning_briefing",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Job scheduled for {settings.BRIEFING_TIME_HOUR}:{settings.BRIEFING_TIME_MINUTE:02d}")
    return scheduler
