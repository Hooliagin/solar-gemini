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

async def start_command(update: Update, context):
    """Handle /start command - saves user's chat_id to database."""
    chat_id = str(update.effective_chat.id)
    
    try:
        # Get or create user settings
        session = next(get_session())
        user_settings = session.query(UserSettings).first()
        
        if not user_settings:
            user_settings = UserSettings()
            session.add(user_settings)
        
        user_settings.telegram_chat_id = chat_id
        user_settings.telegram_enabled = True
        user_settings.updated_at = datetime.utcnow()
        session.commit()
        session.close()
        
        await update.message.reply_text(
            "✅ Verbunden! Du bekommst ab jetzt dein Morgen-Briefing hier.\n\n"
            "Befehle:\n"
            "/generate - Briefing sofort erstellen\n"
            "Sprachnachricht senden - Als Tagebuch-Eintrag speichern"
        )
        
    except Exception as e:
        logger.error(f"Error in /start command: {e}")
        await update.message.reply_text("❌ Fehler beim Verbinden. Bitte später erneut versuchen.")

async def generate_command(update: Update, context):
    """Handle /generate command - triggers immediate briefing generation."""
    await update.message.reply_text("⏳ Briefing wird generiert... Das kann bis zu 60 Sekunden dauern.")
    
    try:
        from services.content_generator import generate_briefing_content
        
        # Trigger briefing generation (this will also send via Telegram if enabled)
        await asyncio.to_thread(generate_briefing_content)
        
        await update.message.reply_text("✅ Briefing wurde erstellt!")
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        await update.message.reply_text(f"❌ Fehler: {str(e)}")

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

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    Receives updates from Telegram and processes them.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        app = get_application()
        update_data = await request.json()
        update = Update.de_json(update_data, app.bot)
        
        # Process update
        await app.process_update(update)
        
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
