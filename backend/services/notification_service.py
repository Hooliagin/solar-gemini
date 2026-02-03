import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from models import Briefing, UserSettings
from services.telegram_service import send_briefing_audio, send_text_message
from services.image_service import generate_agenda_image, generate_weekly_agenda_image

logger = logging.getLogger(__name__)

async def deliver_briefing_notification(user_settings: UserSettings, briefing: Briefing):
    """
    Delivers a briefing notification to the user via Telegram.
    Includes a greeting, an agenda image (if applicable), and the briefing audio.
    """
    if not user_settings.telegram_enabled or not user_settings.telegram_chat_id:
        logger.info(f"Telegram notification disabled or chat ID missing for user {user_settings.user_id}")
        return

    try:
        chat_id = user_settings.telegram_chat_id
        b_type = briefing.type or "daily"
        
        # 1. Send Greeting
        greeting_text = "🚀 **Dein Briefing ist bereit!**"
        if b_type == "weekly":
            greeting_text = "📅 **Deine Weekly Vision ist bereit!**"
        
        await send_text_message(chat_id=chat_id, text=greeting_text)
        
        # 2. Generate Agenda Image
        agenda_image_path = None
        if briefing.calendar_events:
            try:
                events = json.loads(briefing.calendar_events)
                
                if b_type == "weekly":
                    start_str = datetime.now().strftime("%d.%m")
                    end_str = (datetime.now() + timedelta(days=6)).strftime("%d.%m")
                    week_str = f"Woche vom {start_str}"
                    agenda_image_path = generate_weekly_agenda_image(events, week_str)
                else:
                    date_str = datetime.now().strftime("%A, %d. %B")
                    agenda_image_path = generate_agenda_image(events, date_str)
                    
            except Exception as e:
                logger.error(f"Failed to generate agenda image: {e}")

        # 3. Send Audio with Image and Caption
        caption = f"🌅 Dein Morgen-Briefing für {datetime.now().strftime('%d.%m.%Y')}"
        if b_type == "weekly":
            caption = f"📅 Deine Weekly Vision vom {datetime.now().strftime('%d.%m.%Y')}"

        await send_briefing_audio(
            chat_id=chat_id,
            audio_path=briefing.audio_path,
            caption=caption,
            image_path=agenda_image_path
        )
        
        logger.info(f"Briefing notification delivered to user {user_settings.user_id} via Telegram")
        
    except Exception as e:
        logger.error(f"Error delivering briefing notification for user {user_settings.user_id}: {e}")
