"""
Telegram Bot router - handles webhook and commands.
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import get_session
from models import UserSettings, Entry
from services import audio_service
from datetime import datetime
from config import settings
import logging
import asyncio
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

# Initialize bot application
application = None

def get_application():
    """Get or create Telegram application."""
    global application
    if application is None and settings.TELEGRAM_BOT_TOKEN:
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("generate", generate_command))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    
    return application


from sqlalchemy import or_

async def start_command(update: Update, context):
    """
    Handle /start command.
    Usage: /start <link_code>
    Links Telegram chat_id to the user who generated the code.
    """
    args = context.args
    chat_id = str(update.effective_chat.id)
    
    if not args:
        await update.message.reply_text(
            "👋 Hallo! Um diesen Bot zu nutzen, musst du ihn mit deinem Account verknüpfen.\n\n"
            "Gehe in der Web-App auf 'Einstellungen' -> 'Telegram verbinden' und sende mir den Code:\n"
            "Beispiel: `/start 123456`"
        )
        return

    link_code = args[0]
    
    try:
        session = next(get_session())
        # Find user settings with this link token
        statement = select(UserSettings).where(UserSettings.telegram_link_token == link_code)
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            await update.message.reply_text("❌ Ungültiger oder abgelaufener Code. Bitte generiere einen neuen.")
            session.close()
            return
            
        # Link accounts
        user_settings.telegram_chat_id = chat_id
        user_settings.telegram_enabled = True
        user_settings.telegram_link_token = None # Invalidate token after use
        user_settings.updated_at = datetime.utcnow()
        session.add(user_settings)
        session.commit()
        session.close()
        
        await update.message.reply_text(
            "✅ Erfolgreich verbunden! Du bekommst ab jetzt dein Morgen-Briefing hier.\n\n"
            "Befehle:\n"
            "/generate - Briefing sofort erstellen\n"
            "Sprachnachricht senden - Als Tagebuch-Eintrag speichern"
        )
        
    except Exception as e:
        logger.error(f"Error in /start command: {e}")
        await update.message.reply_text("❌ Fehler beim Verbinden.")



async def handle_voice_message(update: Update, context):
    """Handle voice messages - transcribe and save as diary entry."""
    await update.message.reply_text("🎙️ Verarbeite Sprachnachricht...")
    
    try:
        # Download voice file
        voice = update.message.voice
        file = await voice.get_file()
        
        # Save temporarily
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        temp_path = os.path.join(settings.AUDIO_DIR, f"telegram_{voice.file_id}.ogg")
        await file.download_to_drive(temp_path)
        
        # Transcribe
        transcription_result = audio_service.transcribe_audio(temp_path)
        transcript = transcription_result.get("text", "") if isinstance(transcription_result, dict) else transcription_result
        language = transcription_result.get("language", "de") if isinstance(transcription_result, dict) else "de"
        
        # Save as entry
        session = next(get_session())
        entry = Entry(
            audio_path=temp_path,
            transcript=transcript,
            language=language
        )
        session.add(entry)
        session.commit()
        session.close()
        
        await update.message.reply_text(
            f"✅ Tagebuch-Eintrag gespeichert!\n\n"
            f"📝 \"{transcript[:100]}{'...' if len(transcript) > 100 else ''}\""
        )
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text("❌ Fehler beim Verarbeiten der Sprachnachricht.")

from fastapi import BackgroundTasks
from telegram import Bot

from sqlmodel import select, Session

async def run_generation_task(chat_id: str):
    """Background task for briefing generation."""
    try:
        # Initialize a fresh bot instance
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        # 1. Resolve user_id from chat_id
        session = next(get_session())
        statement = select(UserSettings).where(UserSettings.telegram_chat_id == str(chat_id))
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            await bot.send_message(chat_id=chat_id, text="❌ Dein Account ist nicht verknüpft. Bitte nutze /start <code_aus_web_app>.")
            session.close()
            return
            
        user_id = user_settings.user_id
        session.close()
        
        from services.content_generator import generate_briefing_content
        
        # 2. Generate content for this specific user
        await asyncio.to_thread(generate_briefing_content, user_id)
        
        await bot.send_message(chat_id=chat_id, text="✅ Briefing wurde erstellt!")
        
    except Exception as e:
        logger.error(f"Error in background generation: {e}")
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
            await bot.send_message(chat_id=chat_id, text=f"❌ Fehler: {error_msg}")
        except Exception:
            pass

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook endpoint.
    Receives updates from Telegram and processes them.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        # Build fresh application for each request
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Define handlers wrapper to access background_tasks
        async def generate_wrapper(update: Update, context):
            await update.message.reply_text("⏳ Briefing wird generiert... Ich sende es dir, sobald es fertig ist.")
            # Add to background tasks - returns immediately to Telegram
            background_tasks.add_task(run_generation_task, update.effective_chat.id)

        # Register handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("generate", generate_wrapper))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        
        # Initialize the application
        await app.initialize()
        await app.start()
        
        # Process the update
        update_data = await request.json()
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
        # Cleanup
        await app.stop()
        await app.shutdown()
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def telegram_status(session: Session = Depends(get_session)):
    """Check if Telegram bot is connected."""
    user_settings = session.query(UserSettings).first()
    
    if not user_settings or not user_settings.telegram_chat_id:
        return {"connected": False}
    
    return {
        "connected": user_settings.telegram_enabled,
        "chat_id": user_settings.telegram_chat_id
    }
