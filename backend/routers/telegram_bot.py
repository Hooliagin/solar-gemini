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



# --- Onboarding Funnel ---

from telegram.ext import ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# States
CITY, VOICE, NEWS, INTERESTS, CALENDAR = range(5)

async def start_onboarding(update: Update, context):
    """Entry point for the conversation."""
    chat_id = str(update.effective_chat.id)
    
    # Check/Create User
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if not user:
        import uuid
        new_id = str(uuid.uuid4())
        user = UserSettings(
            user_id=new_id,
            telegram_chat_id=chat_id,
            telegram_enabled=True,
            updated_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
    session.close()

    await update.message.reply_text(
        "👋 **Willkommen beim Daily Voice Manager!** ☀️\n\n"
        "Ich bin dein persönlicher KI-Assistent. Lass uns kurz alles einrichten, damit dein Morgen-Briefing perfekt wird.\n\n"
        "1️⃣ **Wo wohnst du?** (Für Wetter & lokale News)\n"
        "Bitte gib deine Stadt ein (z.B. *Berlin*):",
        parse_mode='Markdown'
    )
    return CITY

async def city_state(update: Update, context):
    """Save city and ask for voice."""
    city = update.message.text
    chat_id = str(update.effective_chat.id)
    
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    if user:
        user.weather_city = city
        user.weather_enabled = True
        session.add(user)
        session.commit()
    session.close()
    
    # Ask for Voice
    keyboard = [
        [InlineKeyboardButton("Alloy (Neutral)", callback_data='voice_alloy')],
        [InlineKeyboardButton("Echo (Warm)", callback_data='voice_echo')],
        [InlineKeyboardButton("Nova (Freundlich)", callback_data='voice_nova')],
        [InlineKeyboardButton("Onyx (Tief)", callback_data='voice_onyx')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Stadt **{city}** gespeichert.\n\n"
        "2️⃣ **Welche Stimme soll ich nutzen?**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return VOICE

async def voice_state(update: Update, context):
    """Save voice and ask for news."""
    query = update.callback_query
    await query.answer()
    
    voice = query.data.replace("voice_", "")
    chat_id = str(update.effective_chat.id)
    
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    if user:
        user.voice_id = voice
        session.add(user)
        session.commit()
    session.close()
    
    # Save context for news toggles
    context.user_data['news_selection'] = {
        "politics": True, "local": True, "economy": False, "tech": False, "sports": False
    }
    
    await show_news_keyboard(query.message, context.user_data['news_selection'])
    return NEWS

async def show_news_keyboard(message, selection):
    """Helper to render news toggle keyboard."""
    def btn_text(key, name):
        return f"{'✅' if selection[key] else '❌'} {name}"
        
    keyboard = [
        [
            InlineKeyboardButton(btn_text("politics", "Politik"), callback_data='toggle_politics'),
            InlineKeyboardButton(btn_text("local", "Lokal"), callback_data='toggle_local')
        ],
        [
            InlineKeyboardButton(btn_text("economy", "Wirtschaft"), callback_data='toggle_economy'),
            InlineKeyboardButton(btn_text("tech", "Tech"), callback_data='toggle_tech')
        ],
        [InlineKeyboardButton(btn_text("sports", "Sport"), callback_data='toggle_sports')],
        [InlineKeyboardButton("➡️ Weiter", callback_data='news_done')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "3️⃣ **Welche News interessieren dich?**\n"
        "Klicke zum An/Abwählen. Wenn fertig, klicke 'Weiter'."
    )
    
    # Edit or send new
    if message.text == text.replace("*", ""): # Avoid editing if same content (simplified check)
        await message.edit_reply_markup(reply_markup=reply_markup)
    else:
        try:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except: # If message cannot be edited (e.g. was simple text before)
            await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def news_state(update: Update, context):
    """Handle news toggles."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'news_done':
        # Save to DB
        chat_id = str(update.effective_chat.id)
        selection = context.user_data['news_selection']
        
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        if user:
            user.news_politics = selection['politics']
            user.news_local = selection['local']
            user.news_economy = selection['economy']
            user.news_tech = selection['tech']
            user.news_sports = selection['sports']
            session.add(user)
            session.commit()
        session.close()
        
        await query.message.reply_text(
            "4️⃣ **Hast du spezielle Interessen?**\n\n"
            "Schreibe mir Themen, die dich interessieren, getrennt durch Kommas.\n"
            "Beispiel: _Künstliche Intelligenz, FC Bayern, Vegan Kochen_\n\n"
            "(Schreibe 'keine', um zu überspringen)",
            parse_mode='Markdown'
        )
        return INTERESTS
        
    # Toggle
    cat = data.replace('toggle_', '')
    if cat in context.user_data['news_selection']:
        context.user_data['news_selection'][cat] = not context.user_data['news_selection'][cat]
        await show_news_keyboard(query.message, context.user_data['news_selection'])
        
    return NEWS

async def interests_state(update: Update, context):
    """Save interests and ask for calendar."""
    text = update.message.text
    chat_id = str(update.effective_chat.id)
    
    if text.lower() != 'keine':
        topics = [t.strip() for t in text.split(',') if t.strip()]
        
        session = next(get_session())
        # Delete old interests
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        
        if user:
            # Clear existing interests for this user
            # Need to select interests manually since we don't have relationship loaded or cascade might vary
            from models import Interest
            stmt_del = select(Interest).where(Interest.user_id == user.user_id)
            existing_interests = session.exec(stmt_del).all()
            for i in existing_interests:
                session.delete(i)
                
            # Add new
            for topic in topics:
                session.add(Interest(topic=topic, user_id=user.user_id))
            session.commit()
        session.close()

    # Calendar Step
    from config import settings
    # We need user_id for the OAuth state
    session = next(get_session())
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    session.close()
    
    # Construct OAuth URL manually or via helper
    # Simulating helper logic here for simplicity, assuming API URL
    # Real URL should be: API_URL + /auth/google?user_id=... but the auth endpoint expects Bearer usually
    # But wait, our /auth/google endpoint takes user_id from DEPENDS. That works for web with token.
    # For Telegram, we need a special endpoint or we construct the Google URL directly here.
    # Direct construction is safer/easier if we have client params.
    
    # Let's direct them to the backend endpoint but we need to pass user_id.
    # We can modify /auth/google to accept query param 'user_id' OR token.
    # Or simpler: Just tell them to use the Web App for Calendar for now, or link to the endpoint with a temp token?
    # The 'state' param in OAuth is key.
    # Let's assume we can link to: {API_URL}/auth/google_login?telegram_user_id={user_id} -> Redirects to Google
    
    # For now, simplistic approach: Link to Web App Settings? Or skip calendar?
    # User asked for Flow. Let's provide a link to the backend endpoint that initiates the flow.
    # Note: I need to update google_auth.py to allow 'telegram_user_id' param if I do this.
    
    # Fallback: Just done message.
    await update.message.reply_text(
        "🎉 **Perfekt! Dein Setup ist fertig.**\n\n"
        "Du kannst jetzt:\n"
        "🎤 Mir Sprachnachrichten schicken -> Tagebuch\n"
        "🌅 `/generate` tippen -> Dein persönliches Briefing\n\n"
        "⚠️ **Google Kalender:**\n"
        "Um Termine einzubinden, nutze bitte diesen Link (Web-Login erforderlich):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Kalender verbinden 📅", url="https://daily-manager-frontend.onrender.com")]
        ]),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

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
    import random, string
    code = ''.join(random.choices(string.digits, k=6))
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

# --- End Onboarding ---

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Telegram webhook endpoint."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        async def generate_wrapper(update: Update, context):
            await update.message.reply_text("⏳ Briefing wird generiert...")
            background_tasks.add_task(run_generation_task, update.effective_chat.id)

        # Conversation Handler for Onboarding
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", start_onboarding),
                CommandHandler("setup", start_onboarding)
            ],
            states={
                CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_state)],
                VOICE: [CallbackQueryHandler(voice_state, pattern='^voice_')],
                NEWS: [CallbackQueryHandler(news_state, pattern='^(toggle_|news_done)')],
                INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, interests_state)],
            },
            fallbacks=[CommandHandler("cancel", cancel_onboarding)]
        )
        
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("generate", generate_wrapper))
        app.add_handler(CommandHandler("login", login_command))
        
        # Existing Settings Commands (keeping them for quick access)
        app.add_handler(CommandHandler("settings", settings_command))
        app.add_handler(CommandHandler("set_city", set_city_command))
        app.add_handler(CommandHandler("set_voice", set_voice_command))
        app.add_handler(CommandHandler("toggle_news", toggle_news_command))
        
        app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        
        await app.initialize()
        await app.start()
        
        update_data = await request.json()
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
        
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
