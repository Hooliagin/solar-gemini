"""
Telegram Bot router - handles webhook and commands.
"""
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select, text
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
        application.add_handler(CommandHandler("unlink", unlink_command))
        application.add_handler(CommandHandler("reset", unlink_command))
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
    
    import uuid
    
    if not args:
        # Check if user already exists
        session = next(get_session())
        statement = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        existing_user = session.exec(statement).first()
        
        if existing_user:
             await update.message.reply_text(
                "✅ Du bist bereits verbunden!\n"
                "Sende mir eine Sprachnachricht für dein Tagebuch oder nutze /generate."
            )
             session.close()
             return

        # New User Signup (Telegram Only)
        new_user_id = str(uuid.uuid4())
        new_user = UserSettings(
            user_id=new_user_id,
            telegram_chat_id=chat_id,
            telegram_enabled=True,
            updated_at=datetime.utcnow()
        )
        session.add(new_user)
        session.commit()
        session.close()
        
        await update.message.reply_text(
            "🎉 **Willkommen!**\n\n"
            "Ich habe dir einen neuen Account erstellt. Du kannst diesen Bot jetzt sofort nutzen, ohne Web-Login.\n\n"
            "**Befehle:**\n"
            "🎤 Sende eine Sprachnachricht -> Tagebuch-Eintrag\n"
            "🌅 /generate -> Morgen-Briefing erstellen\n"
            "⚙️ (Bald) Einstellungen hier ändern"
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
            
        # Check if chat_id is already linked to ANOTHER user (Shadow User)
        # This happens if user started with Telegram (creating a user_id) but then linked a Web Account (different user_id)
        stmt_shadow = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        shadow_user = session.exec(stmt_shadow).first()
        
        target_user_id = user_settings.user_id
        
        if shadow_user and shadow_user.user_id != target_user_id:
            logger.info(f"Merging Shadow User {shadow_user.user_id} into Target User {target_user_id}")
            
            # Migrate Data
            # Move Entries
            session.exec(text(f"UPDATE entry SET user_id = '{target_user_id}' WHERE user_id = '{shadow_user.user_id}'"))
            # Move Briefings
            session.exec(text(f"UPDATE briefing SET user_id = '{target_user_id}' WHERE user_id = '{shadow_user.user_id}'"))
            # Move Todos
            session.exec(text(f"UPDATE usertodo SET user_id = '{target_user_id}' WHERE user_id = '{shadow_user.user_id}'"))
            # Move ResearchTasks
            session.exec(text(f"UPDATE researchtask SET user_id = '{target_user_id}' WHERE user_id = '{shadow_user.user_id}'"))
            
            # Move Interests (Handle duplicates? For now just overwrite)
            session.exec(text(f"UPDATE interest SET user_id = '{target_user_id}' WHERE user_id = '{shadow_user.user_id}'"))
            
            # Delete Shadow User Settings
            session.delete(shadow_user)
            session.flush() # Commit delete first to free up the unique telegram_chat_id constraint
            
        # Link accounts
        user_settings.telegram_chat_id = chat_id
        user_settings.telegram_enabled = True
        user_settings.telegram_link_token = None # Invalidate token after use
        user_settings.updated_at = datetime.utcnow()
        session.add(user_settings)
        session.commit()
        session.close()
        
        await update.message.reply_text(
            f"✅ **Erfolgreich verbunden!**\n"
            f"Deine Accounts wurden zusammengeführt.\n"
            f"Du findest alle deine bisherigen Telegram-Daten jetzt auch im Web.\n\n"
            "Befehle:\n"
            "/generate - Briefing sofort erstellen\n"
            "Sprachnachricht senden - Als Tagebuch-Eintrag speichern"
        )
        
    except Exception as e:
        logger.error(f"Error in /start command: {e}")
        await update.message.reply_text("❌ Fehler beim Verbinden.")

async def unlink_command(update: Update, context):
    """
    Handle /unlink or /reset command.
    Disconnects the current Telegram chat from ANY linked user.
    """
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("⏳ Trenne Verbindung...", parse_mode='Markdown')
    logger.info(f"Unlinking chat_id: {chat_id}")
    
    try:
        session = next(get_session())
        # Find ANY user with this chat_id
        statement = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(statement).first()
        
        if not user:
            logger.info(f"No user found to unlink for chat_id {chat_id}")
            await update.message.reply_text(
                "ℹ️ Dein Account ist momentan gar nicht verknüpft.\n"
                "Sende /start <code_aus_web_app> um ihn zu verbinden."
            )
            session.close()
            return

        logger.info(f"Unlinking user {user.user_id}")
        # Unlink
        user.telegram_chat_id = None
        user.telegram_enabled = False
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.close()
        logger.info("Unlink success")
        
        await update.message.reply_text(
            "✅ **Verbindung gelöscht.**\n\n"
            "Dein Telegram-Account wurde von deinem Daily-Manager-Profil getrennt.\n"
            "Du kannst ihn jetzt mit einem neuen Profil verknüpfen.\n\n"
            "Nutze dazu im neuen Profil den Code und sende:\n"
            "/start <code_aus_web_app>"
        )
        
    except Exception as e:
        logger.error(f"Error in /unlink command: {e}")
        await update.message.reply_text("❌ Fehler beim Trennen der Verbindung.")


# ... Onboarding Code Skipped ...

# ... inside login_command ...
async def login_command(update: Update, context):
    """Generate a login link for the web interface."""
    chat_id = str(update.effective_chat.id)
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if not user:
        await update.message.reply_text("❌ Bitte starte erst mit /start.")
        session.close()
        return

    # Generate token
    import uuid
    code = uuid.uuid4().hex[:12]
    user.telegram_link_token = code
    session.add(user)
    session.commit()
    session.close()

    url = f"https://daily-manager-frontend.onrender.com/?claim_code={code}"
    await update.message.reply_text(
        f"🔗 **Web-Account verknüpfen**\n\n"
        f"Klicke auf diesen Link, um dich im Web einzuloggen und deine Daten mitzunehmen:\n"
        f"👉 [Hier klicken]({url})\n\n"
        f"(Code: `{code}`)",
        parse_mode='Markdown'
    )

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
        
        session = next(get_session())
        
        # Verify user mapping
        chat_id = str(update.effective_chat.id)
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        
        if not user:
             logger.error(f"Telegram user {chat_id} not found/linked during voice upload.")
             await update.message.reply_text("❌ Fehler: Dein Account ist nicht verknüpft.")
             session.close()
             return

        logger.info(f"Processing voice for Telegram User {chat_id} -> App User {user.user_id}")

        entry = Entry(
            audio_path=temp_path,
            transcript=transcript,
            language=language,
            user_id=user.user_id
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

# --- End Onboarding ---

async def onboarding_text_router(update: Update, context):
    """Route text messages based on user's onboarding step in database."""
    chat_id = str(update.effective_chat.id)
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        step = user.onboarding_step if user else None
        session.close()
    except Exception as e:
        logger.error(f"Error getting onboarding step: {e}")
        return
    
    if step == STEP_NAME:
        await name_state(update, context)
    elif step == STEP_AGE:
        await age_state(update, context)
    elif step == STEP_CITY:
        await city_state(update, context)
    elif step == STEP_INTERESTS:
        await interests_state(update, context)
    else:
        # User is not in onboarding, just acknowledge
        pass

async def onboarding_callback_router(update: Update, context):
    """Route callback queries based on pattern (voice/news buttons)."""
    query = update.callback_query
    data = query.data
    
    if data.startswith('voice_'):
        await voice_state(update, context)
    elif data.startswith('toggle_') or data == 'news_done':
        await news_state(update, context)

def run_generation_task(chat_id: int):
    """Background task to generate and send a briefing."""
    import asyncio
    from services.content_generator import generate_briefing_content
    from services.telegram_service import send_briefing_audio, send_text_message
    
    chat_id_str = str(chat_id)
    
    # Get user by chat_id
    session = next(get_session())
    try:
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id_str)
        user = session.exec(stmt).first()
        
        if not user:
            logger.error(f"No user found for chat_id {chat_id}")
            return
            
        user_id = user.user_id
    finally:
        session.close()
    
    try:
        # Generate briefing
        logger.info(f"Generating briefing for user {user_id}")
        briefing = generate_briefing_content(user_id)
        
        if briefing and briefing.audio_path:
            async def send():
                await send_briefing_audio(
                    chat_id=chat_id_str,
                    audio_path=briefing.audio_path,
                    caption=f"🌅 Dein persönliches Briefing"
                )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(send())
            finally:
                loop.close()
                
            logger.info(f"Briefing sent to chat {chat_id}")
        else:
            # Send error message
            async def send_error():
                await send_text_message(chat_id_str, "❌ Fehler beim Generieren des Briefings. Bitte versuche es später nochmal.")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(send_error())
            finally:
                loop.close()
                
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Telegram webhook endpoint."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        # Read and log raw body
        body = await request.body()
        logger.info(f"Telegram Webhook received: {body.decode('utf-8')}")
        
        # Parse update manually first to ensure we don't depend on App build for logging
        update_data = await request.json()
        
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        async def generate_wrapper(update: Update, context):
            await update.message.reply_text("⏳ Briefing wird generiert...")
            background_tasks.add_task(run_generation_task, update.effective_chat.id)

        # Commands
        app.add_handler(CommandHandler("start", start_onboarding))
        app.add_handler(CommandHandler("setup", start_onboarding))
        app.add_handler(CommandHandler("generate", generate_wrapper))
        app.add_handler(CommandHandler("login", login_command))
        app.add_handler(CommandHandler("cancel", cancel_onboarding)) # Singular
        app.add_handler(CommandHandler("unlink", unlink_command))
        app.add_handler(CommandHandler("reset", unlink_command))
        app.add_handler(CommandHandler("settings", settings_command))
        app.add_handler(CommandHandler("set_city", set_city_command))
        app.add_handler(CommandHandler("set_voice", set_voice_command))
        app.add_handler(CommandHandler("toggle_news", toggle_news_command))
        
        # Callback queries (inline buttons)
        app.add_handler(CallbackQueryHandler(onboarding_callback_router))
        
        # Voice messages
        app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        
        # Text messages - route based on database step
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_text_router))
        
        await app.initialize()
        await app.start()
        
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
        await app.stop()
        await app.shutdown()
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook CRITICAL ERROR: {e}", exc_info=True)
        # Even if error, return 200 to stop Telegram retries if it's a code error
        return {"ok": True}

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

@router.get("/scheduler-debug")
def scheduler_debug(session: Session = Depends(get_session)):
    """Debug endpoint to check scheduler status and eligible users."""
    from datetime import datetime, timedelta
    from services.scheduler import get_users_due_for_briefing
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    # Get all users with Telegram enabled
    all_telegram_users = session.exec(
        select(UserSettings).where(UserSettings.telegram_enabled == True)
    ).all()
    
    # Get users due for briefing now
    due_users = get_users_due_for_briefing()
    
    return {
        "current_time": current_time,
        "datetime_now": now.isoformat(),
        "telegram_users_count": len(all_telegram_users),
        "telegram_users": [
            {
                "user_id": u.user_id,
                "name": u.name,
                "briefing_time": u.briefing_time,
                "telegram_chat_id": u.telegram_chat_id,
                "telegram_enabled": u.telegram_enabled
            } for u in all_telegram_users
        ],
        "due_for_briefing_count": len(due_users),
        "due_users": [{"user_id": u.user_id, "briefing_time": u.briefing_time} for u in due_users]
    }

@router.post("/trigger-scheduler")
def trigger_scheduler(session: Session = Depends(get_session)):
    """Manually trigger the scheduler job for testing."""
    from services.scheduler import scheduled_briefing_job
    import threading
    
    threading.Thread(target=scheduled_briefing_job, daemon=True).start()
    
    return {"status": "triggered", "message": "Scheduler job triggered in background"}

# --- Settings Commands ---

async def settings_command(update: Update, context):
    """Show current settings."""
    chat_id = str(update.effective_chat.id)
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    session.close()

    if not user:
        await update.message.reply_text("❌ Kein Account gefunden. Nutze /start.")
        return

    text = (
        "⚙️ **Deine Einstellungen:**\n\n"
        f"🏙️ **Stadt:** {user.weather_city or 'Nicht gesetzt'} (`/set_city Berlin`)\n"
        f"🗣️ **Stimme:** {user.voice_id} (`/set_voice alloy`)\n"
        f"⛅ **Wetter:** {'✅' if user.weather_enabled else '❌'}\n"
        "\n📰 **News Kategorien:** (`/toggle_news <kat>`)\n"
        f"- Politik: {'✅' if user.news_politics else '❌'} (politics)\n"
        f"- Lokal: {'✅' if user.news_local else '❌'} (local)\n"
        f"- Wirtschaft: {'✅' if user.news_economy else '❌'} (economy)\n"
        f"- Tech: {'✅' if user.news_tech else '❌'} (tech)\n"
        f"- Sport: {'✅' if user.news_sports else '❌'} (sports)\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_city_command(update: Update, context):
    """Set weather city."""
    if not context.args:
        await update.message.reply_text("❌ Bitte Stadt angeben: `/set_city Berlin`")
        return
    
    city = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if user:
        user.weather_city = city
        user.weather_enabled = True
        session.add(user)
        session.commit()
        await update.message.reply_text(f"✅ Stadt auf **{city}** gesetzt (Wetter aktiviert).")
    session.close()

async def set_voice_command(update: Update, context):
    """Set TTS voice."""
    valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    if not context.args or context.args[0] not in valid_voices:
        await update.message.reply_text(f"❌ Ungültig. Verfügbar: {', '.join(valid_voices)}\nBsp: `/set_voice alloy`")
        return
    
    voice = context.args[0]
    chat_id = str(update.effective_chat.id)
    
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if user:
        user.voice_id = voice
        session.add(user)
        session.commit()
        await update.message.reply_text(f"✅ Stimme auf **{voice}** geändert.")
    session.close()

async def toggle_news_command(update: Update, context):
    """Toggle news category."""
    map_cat = {
        "politics": "news_politics",
        "local": "news_local",
        "economy": "news_economy",
        "tech": "news_tech",
        "sports": "news_sports"
    }
    
    if not context.args or context.args[0] not in map_cat:
        await update.message.reply_text(f"❌ Ungültig. Verfügbar: {', '.join(map_cat.keys())}\nBsp: `/toggle_news tech`")
        return
        
    cat_key = map_cat[context.args[0]]
    chat_id = str(update.effective_chat.id)
    
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if user:
        current = getattr(user, cat_key, False)
        setattr(user, cat_key, not current)
        session.add(user)
        session.commit()
        await update.message.reply_text(f"✅ {context.args[0]} {'aktiviert' if not current else 'deaktiviert'}.")
    session.close()
