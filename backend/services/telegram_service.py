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

async def send_briefing_audio(chat_id: str, audio_path: str, caption: str = None, image_path: str = None):
    """
    Sends briefing audio file to Telegram chat.
    Optionally sends an agenda image first.
    
    Args:
        chat_id: Telegram chat ID
        audio_path: Absolute path to audio file
        caption: Optional caption (max 1024 chars)
        image_path: Optional path to agenda image
    """
    try:
        bot = get_bot()
        
        # 1. Send Image if provided
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as photo:
                    await bot.send_photo(chat_id=chat_id, photo=photo)
            except Exception as e:
                logger.error(f"Failed to send agenda image: {e}")

        if not audio_path:
            logger.error("Audio path not provided")
            return False

        # Support for Supabase Storage Paths (Format: "user_id/filename.wav")
        is_storage_path = "/" in audio_path and not audio_path.startswith("/") and not ":" in audio_path
        
        voice_input = None
        
        if is_storage_path:
            # Download file content to memory to ensure Telegram can send it reliably
            # (Passing URLs sometimes fails if Telegram servers can't reach the signed link or if it's redirects)
            from services.storage_service import download_file
            try:
                logger.info(f"Downloading audio from storage for Telegram: {audio_path}")
                file_bytes = download_file(audio_path)
                voice_input = file_bytes # Telegram accepts bytes if we don't set a filename, but better to wrap
            except Exception as e:
                logger.error(f"Failed to download file for Telegram: {e}")
                return False
        
        elif os.path.exists(audio_path):
            # Local File
            voice_input = open(audio_path, 'rb')
        else:
            logger.error(f"Audio file not found (Local or Storage): {audio_path}")
            return False
            
        # Send
        try:
            await bot.send_voice(
                chat_id=chat_id,
                voice=voice_input,
                caption=caption[:1024] if caption else None
            )
        finally:
            # Close file if we opened one. Bytes objects don't need closing.
            if hasattr(voice_input, 'close') and callable(voice_input.close):
                voice_input.close()
        
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
