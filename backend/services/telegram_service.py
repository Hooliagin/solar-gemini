"""
Telegram service for sending briefings and handling bot interactions.
"""
from telegram import Bot
from telegram.error import TelegramError
from config import settings
import logging
import os

logger = logging.getLogger(__name__)

def get_bot():
    """Initialize and return Telegram bot instance."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_briefing_audio(chat_id: str, audio_path: str, caption: str = None):
    """
    Sends briefing audio file to Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        audio_path: Absolute path to audio file
        caption: Optional caption (max 1024 chars)
    """
    try:
        bot = get_bot()
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False
        
        with open(audio_path, 'rb') as audio_file:
            await bot.send_voice(
                chat_id=chat_id,
                voice=audio_file,
                caption=caption[:1024] if caption else None
            )
        
        logger.info(f"Briefing sent to Telegram chat {chat_id}")
        return True
        
    except TelegramError as e:
        logger.error(f"Telegram error sending briefing: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending briefing to Telegram: {e}")
        return False

async def send_text_message(chat_id: str, text: str):
    """
    Sends a text message to Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text
    """
    try:
        bot = get_bot()
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramError as e:
        logger.error(f"Telegram error sending message: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return False
