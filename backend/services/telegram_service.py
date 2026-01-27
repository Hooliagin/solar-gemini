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
        # Check if it's a Forbidden error (user blocked bot)
        if "Forbidden" in str(e):
            logger.warning(f"Briefing not sent: Bot blocked by user {chat_id}")
            return False
            
        logger.error(f"Error sending briefing to Telegram: {e}")
        return False

async def send_text_message(chat_id: str, text: str):
    """
    Sends a text message to Telegram chat.
    Splits long messages into chunks (Telegram limit: 4096 chars).
    
    Args:
        chat_id: Telegram chat ID
        text: Message text
    """
    MAX_LENGTH = 4000  # Leave some margin
    
    try:
        bot = get_bot()
        
        # Split long messages into chunks
        if len(text) <= MAX_LENGTH:
            await bot.send_message(chat_id=chat_id, text=text)
        else:
            # Split by paragraphs first, then by length
            chunks = []
            current_chunk = ""
            
            for paragraph in text.split('\n\n'):
                if len(current_chunk) + len(paragraph) + 2 <= MAX_LENGTH:
                    current_chunk += paragraph + '\n\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    # If single paragraph is too long, split by sentences
                    if len(paragraph) > MAX_LENGTH:
                        words = paragraph.split()
                        current_chunk = ""
                        for word in words:
                            if len(current_chunk) + len(word) + 1 <= MAX_LENGTH:
                                current_chunk += word + ' '
                            else:
                                chunks.append(current_chunk.strip())
                                current_chunk = word + ' '
                    else:
                        current_chunk = paragraph + '\n\n'
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                prefix = f"📄 Teil {i+1}/{len(chunks)}\n\n" if len(chunks) > 1 else ""
                await bot.send_message(chat_id=chat_id, text=prefix + chunk)
        
        return True
    except TelegramError as e:
        logger.error(f"Telegram error sending message: {e}")
        return False
    except Exception as e:
        if "Forbidden" in str(e):
            logger.warning(f"Message not sent: Bot blocked by user {chat_id}")
            return False
            
        logger.error(f"Error sending message to Telegram: {e}")
        return False
