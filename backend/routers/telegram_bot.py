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
    logger.info(f"Received /start with args: {context.args}")
    try:
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
    
            # STRICT MODE: No new users via Telegram
            await update.message.reply_text(
                "👋 **Willkommen!**\n\n"
                "Bitte registriere dich zuerst in unserer Web-App:\n"
                "👉 https://daily-manager-frontend.onrender.com\n\n"
                "Dort findest du in den **Einstellungen** einen QR-Code oder Link,\n"
                "um diesen Bot mit deinem Account zu verbinden."
            )
            session.close()
            return
    
        link_code = args[0]

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
            
            # Migrate Data - use parameterized queries to prevent SQL injection
            # Move Entries
            session.exec(text("UPDATE entry SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
            # Move Briefings
            session.exec(text("UPDATE briefing SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
            # Move Todos
            session.exec(text("UPDATE usertodo SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
            # Move ResearchTasks
            session.exec(text("UPDATE researchtask SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
            
            # Move Interests (Handle duplicates? For now just overwrite)
            session.exec(text("UPDATE interest SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
            
            # Delete Shadow User Settings
            session.delete(shadow_user)
            session.flush() # Commit delete first to free up the unique telegram_chat_id constraint
            
        logger.info(f"Linking Chat ID {chat_id} to User {target_user_id}")
        
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
            f"Deine Accounts wurden zusammengeführt.\n\n"
            "Befehle:\n"
            "/generate - Briefing sofort erstellen\n"
            "Sprachnachricht senden - Als Tagebuch-Eintrag speichern"
        )
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in /start command: {e}")
        import traceback
        traceback.print_exc()
        try:
             await update.message.reply_text("❌ Ein kritischer Fehler ist aufgetreten.")
        except:
             pass

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


# --- Onboarding Funnel ---

from telegram.ext import ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# States (now stored in database as strings)
STEP_NAME = 'name'
STEP_AGE = 'age'
STEP_CITY = 'city'
STEP_VOICE = 'voice'
STEP_NEWS = 'news'
STEP_INTERESTS = 'interests'
STEP_DONE = 'done'

# Keep old constants for ConversationHandler compatibility if needed
NAME, AGE, CITY, VOICE, NEWS, INTERESTS = range(6)

async def start_onboarding(update: Update, context):
    """Entry point for the conversation."""
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text if update.message else ""
    
    # Check if this is a /start with a link code (from web app)
    link_code = None
    if message_text.startswith('/start '):
        link_code = message_text.replace('/start ', '').strip()
    
    session = next(get_session())
    
    # First check if user is connecting from web via link code
    if link_code:
        statement = select(UserSettings).where(UserSettings.telegram_link_token == link_code)
        user_settings = session.exec(statement).first() # Fix: use user_settings var name to match below
        
        web_user = user_settings
        
        if web_user:
            # Check if chat_id is already used by a shadow user
            stmt_shadow = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
            shadow_user = session.exec(stmt_shadow).first()
            
            target_user_id = web_user.user_id
            
            if shadow_user and shadow_user.user_id != target_user_id:
                logger.info(f"Merging Shadow User {shadow_user.user_id} into Web User {target_user_id}")
                # Migrate Shadow Data - use parameterized queries to prevent SQL injection
                session.exec(text("UPDATE entry SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
                session.exec(text("UPDATE briefing SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
                session.exec(text("UPDATE usertodo SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
                session.exec(text("UPDATE researchtask SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
                session.exec(text("UPDATE interest SET user_id = :new_id WHERE user_id = :old_id").bindparams(new_id=target_user_id, old_id=shadow_user.user_id))
                session.delete(shadow_user)
                session.flush()

            # Link this Telegram chat to the existing web user
            web_user.telegram_chat_id = chat_id
            web_user.telegram_enabled = True
            web_user.telegram_link_token = None  # Clear the used code
            web_user.onboarding_step = STEP_DONE  # Mark as done
            web_user.updated_at = datetime.utcnow()
            session.add(web_user)
            session.commit()
            session.close()
            
            await update.message.reply_text(
                f"🎉 **Willkommen, {web_user.name or 'Freund'}!**\n\n"
                "Dein Web-Account wurde erfolgreich mit Telegram verbunden! ✅\n\n"
                f"📍 Stadt: **{web_user.weather_city}**\n"
                f"🎙️ Stimme: **{web_user.voice_id}**\n"
                f"⏰ Briefing: **{web_user.briefing_time or '07:00'} Uhr**\n\n"
                "Du kannst jetzt:\n"
                "🎤 Mir Sprachnachrichten schicken → Tagebuch\n"
                "🌅 `/generate` tippen → Dein persönliches Briefing\n"
                "⚙️ `/settings` → Deine Einstellungen anzeigen",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    # Check if user already exists
    stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
    user = session.exec(stmt).first()
    
    if user and user.onboarding_step == STEP_DONE:
        # User already completed onboarding - just welcome back
        session.close()
        await update.message.reply_text(
            f"👋 **Willkommen zurück{', ' + user.name if user.name else ''}!**\n\n"
            "Du hast bereits alles eingerichtet. ✅\n\n"
            "Befehle:\n"
            "🌅 `/generate` - Briefing generieren\n"
            "⚙️ `/settings` - Einstellungen anzeigen\n"
            "🔗 `/unlink` - Account trennen\n"
            "🔄 `/setup` - Setup neu starten (überschreibt alles)",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    if not user:
        import uuid
        new_id = str(uuid.uuid4())
        user = UserSettings(
            user_id=new_id,
            telegram_chat_id=chat_id,
            telegram_enabled=True,
            onboarding_step=STEP_NAME,
            updated_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
    else:
        # Reset onboarding for existing user who hasn't completed
        user.onboarding_step = STEP_NAME
        session.add(user)
        session.commit()
    session.close()

    await update.message.reply_text(
        "👋 **Willkommen beim Daily Voice Manager!** ☀️\n\n"
        "Ich bin dein persönlicher KI-Assistent. Lass uns kurz alles einrichten, damit dein Morgen-Briefing perfekt wird.\n\n"
        "1️⃣ **Wie heißt du?**\n"
        "Bitte gib deinen Namen ein:",
        parse_mode='Markdown'
    )
    return NAME

async def name_state(update: Update, context):
    """Save name and ask for age."""
    name = update.message.text
    chat_id = str(update.effective_chat.id)
    
    context.user_data['name'] = name
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        if user:
            user.name = name
            user.onboarding_step = STEP_AGE
            session.add(user)
            session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error saving name: {e}")
    
    await update.message.reply_text(
        f"✅ Hallo **{name}**!\n\n"
        "2️⃣ **Wie alt bist du?**\n"
        "Bitte gib dein Alter ein:",
        parse_mode='Markdown'
    )
    return AGE

async def age_state(update: Update, context):
    """Save age and ask for city."""
    try:
        age = int(update.message.text)
        if age < 1 or age > 120:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Bitte gib eine gültige Zahl zwischen 1 und 120 ein:")
        return AGE
    
    chat_id = str(update.effective_chat.id)
    context.user_data['age'] = age
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        if user:
            user.age = age
            user.onboarding_step = STEP_CITY
            session.add(user)
            session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error saving age: {e}")
    
    await update.message.reply_text(
        f"✅ Dankeschön!\n\n"
        "3️⃣ **Wo wohnst du?** (Für Wetter & lokale News)\n"
        "Bitte gib deine Stadt ein (z.B. *Hamburg*):",
        parse_mode='Markdown'
    )
    return CITY

async def city_state(update: Update, context):
    """Save city and ask for voice."""
    city = update.message.text
    chat_id = str(update.effective_chat.id)
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        if user:
            user.weather_city = city
            user.weather_enabled = True
            user.onboarding_step = STEP_VOICE
            session.add(user)
            session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error saving city: {e}")
    
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
        "4️⃣ **Welche Stimme soll ich nutzen?**",
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
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        if user:
            user.voice_id = voice
            user.onboarding_step = STEP_NEWS
            session.add(user)
            session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error saving voice: {e}")
    
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
        "5️⃣ **Welche News interessieren dich?**\n"
        "Klicke zum An/Abwählen. Wenn fertig, klicke 'Weiter'."
    )
    
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    except:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def news_state(update: Update, context):
    """Handle news toggles."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'news_done':
        # Save to DB
        chat_id = str(update.effective_chat.id)
        selection = context.user_data.get('news_selection', {
            "politics": True, "local": True, "economy": False, "tech": False, "sports": False
        })
        
        try:
            session = next(get_session())
            stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
            user = session.exec(stmt).first()
            if user:
                user.news_politics = selection.get('politics', True)
                user.news_local = selection.get('local', True)
                user.news_economy = selection.get('economy', False)
                user.news_tech = selection.get('tech', False)
                user.news_sports = selection.get('sports', False)
                user.onboarding_step = STEP_INTERESTS
                session.add(user)
                session.commit()
            session.close()
        except Exception as e:
            logger.error(f"Error saving news: {e}")
        
        
        await query.message.reply_text(
            "6️⃣ **Hast du spezielle Interessen?**\n\n"
            "Schreibe mir Themen, die dich interessieren.\n\n"
            "**Befehle:**\n"
            "`+ Thema` zum Hinzufügen (z.B. `+ KI`, `+ Bitcoin`)\n"
            "`- Thema` zum Entfernen (z.B. `- Fußball`)\n"
            "_Ohne Vorzeichen wird die Liste überschrieben!_\n\n"
            "(Schreibe 'weiter', um fertig zu sein)",
            parse_mode='Markdown'
        )
        return INTERESTS
        
    # Toggle
    cat = data.replace('toggle_', '')
    if 'news_selection' not in context.user_data:
        context.user_data['news_selection'] = {
            "politics": True, "local": True, "economy": False, "tech": False, "sports": False
        }
    if cat in context.user_data['news_selection']:
        context.user_data['news_selection'][cat] = not context.user_data['news_selection'][cat]
        await show_news_keyboard(query.message, context.user_data['news_selection'])
        
    return NEWS

async def interests_state(update: Update, context):
    """Save interests and finish onboarding."""
    text = update.message.text
    chat_id = str(update.effective_chat.id)
    
    try:
        session = next(get_session())
        stmt = select(UserSettings).where(UserSettings.telegram_chat_id == chat_id)
        user = session.exec(stmt).first()
        
        if user:
            from models import Interest
            
            # Fetch existing
            stmt_exist = select(Interest).where(Interest.user_id == user.user_id)
            existing_interests = session.exec(stmt_exist).all()
            current_topics = {i.topic for i in existing_interests}

            text_cleaned = text.strip()
            
            if text_cleaned.lower() == 'weiter' or text_cleaned.lower() == 'keine':
                pass # Just finish
            
            elif text_cleaned.startswith('+'):
                # Add mode
                new_topics = [t.strip() for t in text_cleaned[1:].split(',') if t.strip()]
                for topic in new_topics:
                    if topic not in current_topics:
                        session.add(Interest(topic=topic, user_id=user.user_id))
                        current_topics.add(topic)
                session.commit()
                await update.message.reply_text(f"✅ Hinzugefügt. Aktuell: {', '.join(current_topics)}")
                return INTERESTS # Stay in loop
                
            elif text_cleaned.startswith('-'):
                # Remove mode
                rem_topics = [t.strip().lower() for t in text_cleaned[1:].split(',') if t.strip()]
                for i in existing_interests:
                    if i.topic.lower() in rem_topics:
                        session.delete(i)
                        if i.topic in current_topics:
                            current_topics.remove(i.topic)
                session.commit()
                await update.message.reply_text(f"🗑️ Entfernt. Aktuell: {', '.join(current_topics)}")
                return INTERESTS # Stay in loop

            else:
                # Overwrite mode (default behavior)
                topics = [t.strip() for t in text.split(',') if t.strip()]
                
                # Delete all old
                for i in existing_interests:
                    session.delete(i)
                
                # Add new
                for topic in topics:
                    session.add(Interest(topic=topic, user_id=user.user_id))
                session.commit()
                # Continue below to finish
            
            # Mark onboarding as done
            user.onboarding_step = STEP_DONE
            session.add(user)
            session.commit()
        session.close()
    except Exception as e:
        logger.error(f"Error saving interests: {e}")

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

async def handle_voice_message(update: Update, context):
    """
    Handle voice messages with smart intent classification.
    Routes to: Diary Entry OR Calendar Event based on AI analysis.
    Responds with TTS voice message for a premium assistant feel.
    """
    await update.message.reply_text("🎙️ Ich höre dir zu...")
    
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
             await update.message.reply_text(
                 "❌ Fehler: Dein Account ist nicht verknüpft.\n"
                 "Bitte verbinde dich zuerst über die Web-App."
             )
             session.close()
             return

        logger.info(f"Processing voice for Telegram User {chat_id} -> App User {user.user_id}")
        logger.info(f"Transcript: {transcript[:100]}...")

        # --- INTENT CLASSIFICATION ---
        from google import genai
        from google.genai import types
        import json
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        from services import calendar_service
        from services import tts_service
        
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # Get current time in Berlin for context
        berlin = ZoneInfo("Europe/Berlin")
        now = datetime.now(berlin)
        
        classification_prompt = f"""Du bist ein intelligenter Assistent. Analysiere die folgende Sprachnachricht und klassifiziere sie.

AKTUELLE ZEIT: {now.strftime('%A, %d.%m.%Y um %H:%M Uhr')}

SPRACHNACHRICHT:
"{transcript}"

KLASSIFIZIERE DIE NACHRICHT:
1. "diary" = Persönliche Reflexion, Gedanken, Tagebucheintrag, wie es dem Nutzer geht
2. "calendar" = Der Nutzer möchte einen Termin/Event erstellen (enthält Zeit/Datum und Aktivität)
3. "todo" = Der Nutzer möchte sich etwas merken/eine Aufgabe erstellen (ohne konkretes Datum/Uhrzeit)

BEI "calendar": Extrahiere die Event-Details präzise.
- Berechne das exakte Datum basierend auf "morgen", "nächsten Montag" etc.
- Schätze eine sinnvolle Dauer wenn nicht angegeben (Standard: 60 Minuten)

Antworte NUR mit validem JSON:
{{
  "intent": "diary" | "calendar" | "todo",
  "calendar_event": {{
    "summary": "Termin-Name",
    "start": "YYYY-MM-DDTHH:MM:SS",
    "end": "YYYY-MM-DDTHH:MM:SS",
    "description": "Optional details"
  }} | null,
  "todo_task": "Aufgabe" | null,
  "confidence": 0.0-1.0,
  "assistant_response": "Natürliche Antwort des Assistenten an den Nutzer (max 2 Sätze, freundlich und bestätigend)"
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=classification_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        intent = result.get("intent", "diary")
        confidence = result.get("confidence", 0.5)
        assistant_response = result.get("assistant_response", "Ich habe das für dich notiert.")
        
        logger.info(f"Intent Classification: {intent} (confidence: {confidence})")
        
        # --- ROUTE BASED ON INTENT ---
        if intent == "calendar" and result.get("calendar_event"):
            event_data = result["calendar_event"]
            
            # Check if calendar is connected
            if not user.google_access_token:
                await update.message.reply_text(
                    "📅 Ich würde den Termin gern eintragen, aber dein Kalender ist noch nicht verbunden.\n"
                    "Bitte verbinde Google Calendar in der Web-App."
                )
                session.close()
                return
            
            # Create the event
            success = calendar_service.create_calendar_event(user.user_id, event_data)
            
            if success:
                logger.info(f"Calendar event created: {event_data['summary']}")
                # Generate voice response
                try:
                    response_audio_path = os.path.join(settings.AUDIO_DIR, f"response_{voice.file_id}.wav")
                    tts_service.generate_speech(
                        assistant_response, 
                        response_audio_path, 
                        language=language,
                        voice_override=user.voice_id
                    )
                    
                    # Send voice response
                    with open(response_audio_path, 'rb') as audio_file:
                        await update.message.reply_voice(audio_file)
                    
                    # Cleanup
                    os.remove(response_audio_path)
                except Exception as tts_err:
                    logger.error(f"TTS response failed: {tts_err}")
                    # Fallback to text
                    await update.message.reply_text(f"✅ {assistant_response}")
            else:
                await update.message.reply_text(
                    "❌ Fehler beim Erstellen des Termins. Ist dein Kalender korrekt verbunden?"
                )
        
        elif intent == "todo" and result.get("todo_task"):
            # Save as UserTodo
            from models import UserTodo
            todo = UserTodo(
                user_id=user.user_id,
                task=result["todo_task"]
            )
            session.add(todo)
            session.commit()
            
            # Respond
            await update.message.reply_text(f"✅ {assistant_response}")
        
        else:
            # Default: Save as diary entry
            entry = Entry(
                audio_path=temp_path,
                transcript=transcript,
                language=language,
                user_id=user.user_id
            )
            session.add(entry)
            session.commit()
            
            await update.message.reply_text(
                f"✅ Tagebuch-Eintrag gespeichert!\n\n"
                f"📝\"{transcript[:100]}{'...' if len(transcript) > 100 else ''}\""
            )
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("❌ Fehler beim Verarbeiten der Sprachnachricht.")

def run_generation_task(chat_id: int):
    """Background task to generate and send a briefing via Telegram /generate command."""
    import asyncio
    from services.content_generator import generate_briefing_content
    from services.notification_service import deliver_briefing_notification
    from services.telegram_service import send_text_message
    
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
        
        # Generate briefing
        logger.info(f"Generating briefing for user {user_id}")
        briefing = generate_briefing_content(user_id)
        
        if briefing and briefing.audio_path:
            # Use unified notification service (includes agenda image!)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(deliver_briefing_notification(user, briefing))
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
    finally:
        session.close()

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
        # Commands
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("generate", generate_wrapper))
        app.add_handler(CommandHandler("unlink", unlink_command))
        app.add_handler(CommandHandler("reset", unlink_command))
        app.add_handler(CommandHandler("settings", settings_command))
        app.add_handler(CommandHandler("set_city", set_city_command))
        app.add_handler(CommandHandler("set_voice", set_voice_command))
        app.add_handler(CommandHandler("toggle_news", toggle_news_command))
        
        # Callback queries (inline buttons)
        # app.add_handler(CallbackQueryHandler(onboarding_callback_router)) # Removed
        
        # Voice messages
        app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        
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
    user_settings = session.exec(select(UserSettings)).first()
    
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
