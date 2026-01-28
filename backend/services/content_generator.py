from google import genai
from google.genai import types
from config import settings
from services.calendar_service import get_calendar_events
from services.news_service import fetch_ai_news_summary
from services.weather_service import get_weather_briefing
from services.tts_service import generate_speech
from database import get_session
from sqlmodel import select
from models import Entry, Briefing, UserSettings
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# Configure Gemini (moved inside function to handle missing key gracefully)
# genai.configure(api_key=settings.GOOGLE_API_KEY)

def generate_briefing_content(target_user_id: str):
    """
    Orchestrates the creation of the morning briefing for a SPECIFIC user.
    """
    import sys
    print(f"DEBUG: Starting briefing generation for user {target_user_id}...", flush=True)
    logger.info(f"Starting briefing generation for user {target_user_id}...")
    
    # Validation
    if not settings.GOOGLE_API_KEY:
        print("DEBUG: Missing Google API Key", flush=True)
        raise ValueError("Google Gemini API Key (GEMINI_API_KEY) is missing.")

    # Gemini client will be initialized later when needed
    print("DEBUG: API Key validated.", flush=True)

    session = None
    try:
        session = next(get_session())
        
        # Get user settings
        statement = select(UserSettings).where(UserSettings.user_id == target_user_id)
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            print(f"DEBUG: No settings found for user {target_user_id}. Creating defaults.", flush=True)
            user_settings = UserSettings(user_id=target_user_id)
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)

        # 1. Fetch Calendar
        print("DEBUG: Fetching Calendar...", flush=True)
        # TODO: Pass user tokens to calendar service
        calendar_text = get_calendar_events(target_user_id) 
        print(f"DEBUG: Calendar Fetched ({len(calendar_text)} chars).", flush=True)
        
        # 2. Fetch User Interests & News
        print("DEBUG: Querying Interests...", flush=True)
        from models import Interest
        statement = select(Interest).where(Interest.user_id == target_user_id)
        interests = session.exec(statement).all()
        topic_list = [i.topic for i in interests]
        print(f"DEBUG: Found custom topics: {topic_list}", flush=True)
        
        # ═══════════════════════════════════════════════════════════════
        # PROMPT v2.0 SYSTEM INTEGRATION
        # ═══════════════════════════════════════════════════════════════
        
        # 1. Fetch Split News (Curated vs Dynamic)
        print("DEBUG: Fetching Split News...", flush=True)
        from services.news_service import fetch_all_news
        news_curated, news_dynamic = fetch_all_news(user_settings, topic_list)
        print(f"DEBUG: News Fetched. Curated: {len(news_curated)} chars, Dynamic: {len(news_dynamic)} chars.", flush=True)

        # 2. Fetch History for Anti-Repetition
        # Fetch last 2 briefings to ensure variance
        prev_briefings = session.exec(
            select(Briefing)
            .where(Briefing.user_id == target_user_id)
            .order_by(Briefing.created_at.desc())
            .limit(2)
        ).all()
        
        briefing_yesterday = prev_briefings[0].script_content if len(prev_briefings) > 0 else None
        briefing_day_before = prev_briefings[1].script_content if len(prev_briefings) > 1 else None
        
        # 3. Helper Functions (Embedded)
        import hashlib
        
        def extract_key_phrases(text: str):
            if not text: return []
            sentences = text.replace('!', '.').replace('?', '.').split('.')
            return [s.strip() for s in sentences if 20 < len(s.strip()) < 100][:20]

        def generate_anti_repetition_instruction(yest, day_before):
            if not yest and not day_before: return ""
            instr = "\n════ ANTI-REPETITION (CRITICAL) ════\n"
            instr += "VARIANZ IST PFLICHT. Wiederhole NICHTS von gestern.\n"
            if yest:
                phrases = extract_key_phrases(yest)
                instr += f"GESTERN (VERBOTEN): {yest[:500]}...\nPhrasen zu vermeiden:\n" + "\n".join(f'- "{p}"' for p in phrases[:5]) + "\n"
            return instr

        # 4. Construct Prompt v2.0
        
        # Dynamic date injection
        now = datetime.now()
        current_date_spoken = now.strftime("%A, der %d. %B %Y")
        # German weekday translation
        replacements = {
            "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
            "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag",
            "January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai",
            "June": "Juni", "July": "Juli", "August": "August", "September": "September",
            "October": "Oktober", "November": "November", "December": "Dezember"
        }
        for en, de in replacements.items():
            current_date_spoken = current_date_spoken.replace(en, de)

        anti_repetition = generate_anti_repetition_instruction(briefing_yesterday, briefing_day_before)
        
        prompt = f"""
        You are a friendly, professional personal assistant. It is morning on {current_date_spoken}.
        Create a DETAILED morning briefing script for the user.

        **IMPORTANT: {language_instruction}**
        **GREETING: Address the user as {user_name if user_name else 'my friend'}.**

        **CRITICAL TTS OPTIMIZATION RULES:**
        - NEVER use Markdown formatting (no **, -, #, _, `, etc.)
        - Write EVERYTHING as natural spoken text
        - Spell out ALL numbers as words (e.g., "fünf" not "5", "zehn Uhr" not "10:00")
        - Use full words, NEVER abbreviations (e.g., "zum Beispiel" not "z.B.")
        - Write times in spoken format (e.g., "zehn Uhr dreißig" not "10:30")
        - Use natural pauses with punctuation (commas, periods)
        - Write dates in full spoken form (e.g., "dreiundzwanzigster Januar")
        - **GRAMMAR CHECK**: Ensure perfect German grammar. Use 'hast geschlafen' not 'bist geschlafen'.

        {anti_repetition}

        ═══════════════════════════════════════════════════════════════
        CONTEXT DATA
        ═══════════════════════════════════════════════════════════════

        [YESTERDAY'S DIARY/THOUGHTS]
        {diary_transcript if diary_transcript else "No diary entry available."}

        [USER TODOS / REMINDERS]
        {todo_list_text if todo_list_text else "No todos listed."}

        [RESEARCH RESULTS]
        {research_results_text if research_results_text else "No research requested."}

        [TODAY'S CALENDAR]
        {calendar_text if calendar_text else "No appointments scheduled."}

        [WEATHER]
        {weather_text if weather_text else "Weather data not available."}

        [NEWS - CURATED SOURCES (High Quality)]
        {news_curated}

        [NEWS - DYNAMIC SEARCH (User Topics)]
        {news_dynamic}

        ═══════════════════════════════════════════════════════════════
        ZITAT & STRUKTUR SYSTEM
        ═══════════════════════════════════════════════════════════════

        **ZWEI ZITATE ERFORDERLICH:**

        1. INTENTIONS-ZITAT (Nach Retrospektive):
           - Analysiere Kalender (Meeting-Tag? Ruhiger Tag?)
           - Wähle Zitat das zum TAGESTYP passt (Stoiker, Denker, etc.)
           - Verbinde es direkt mit dem heutigen Tag.

        2. REFLEXIONS-ZITAT (Abschluss):
           - Analysiere Tagebuch (Stress? Erfolg? Sorge?)
           - Wähle Zitat das diese EMOTION anspricht (nicht generisch!)
           - Verbinde es mit der Situation von gestern.

        **STRUKTUR (FLIESSTEXT - Keine Headlines!):**
        1. Warme Begrüßung (Variiere! Nicht wie gestern!)
        2. Tiefe Retrospektive (Was wurde geschafft? Was blieb liegen? Sei empathisch.)
        3. Intentions-Zitat & Vorsätze für heute.
        4. Der Tagesplan (Termine + Todos in die Lücken integrieren).
        5. Recherche-Ergebnisse (falls vorhanden).
        6. News (Mix aus Kuratiert & Dynamisch. Max 2-3 Themen. Nur Relevantes!).
        7. Wetter & Abschluss mit Reflexions-Zitat.

        **STYLE**: Energetic but thoughtful. Like a mentor and a friend.
        **ZIEL**: 3-4 Minuten gesprochener Text.
        """
        
        print("DEBUG: Generating Content with Gemini (v2.0 Prompt)...", flush=True)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        print("DEBUG: Gemini Response Received.", flush=True)
        script = response.text
        
        # 5. Generate Audio
        print("DEBUG: Generating Audio (TTS)...", flush=True)
        audio_filename = f"briefing_{target_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        # Ensure audio directory exists
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        # Get user's preferred voice from settings
        user_voice = user_settings.voice_id if user_settings else None
        generate_speech(script, audio_path_abs, language=detected_language, voice_override=user_voice)
        print(f"DEBUG: Audio saved to {audio_path_abs} (lang: {detected_language}, voice: {user_voice})", flush=True)
        
        # 6. Upload to Supabase Storage (Private Bucket)
        print("DEBUG: Uploading to Supabase...", flush=True)
        from services.storage_service import upload_file, delete_file
        
        # Define a structured path: user_id/filename
        storage_path = f"{target_user_id}/{audio_filename}"
        
        try:
            upload_file(audio_path_abs, storage_path)
            # Delete local file to save space
            if os.path.exists(audio_path_abs):
                os.remove(audio_path_abs)
                print("DEBUG: Local file generated and removed after upload.", flush=True)
        except Exception as e:
            logger.error(f"Upload failed: {e}. Keeping local file as fallback (though it may be lost on restart).")
            storage_path = None # Mark as failed upload
            # We keep audio_path_abs as the "path" but it will be broken on restart. 
            # Ideally we mark this as an error state or retry later.

        # 7. Save Briefing to DB
        briefing = Briefing(
            user_id=target_user_id,
            scheduled_for=datetime.now(),
            script_content=script,
            # If upload worked, save the STORAGE PATH (not URL). If not, save local path (legacy).
            audio_path=storage_path if storage_path else audio_path_abs, 
            status="generated"
        )
        session.add(briefing)
        session.commit()
        session.refresh(briefing)
        session.expunge(briefing) # Allow usage after session closes
        
        logger.info(f"Briefing generated and stored: {storage_path}")
        print("DEBUG: Briefing saved to DB.", flush=True)
        
        # 8. Auto-Cleanup (Rolling Window)
        try:
            print("DEBUG: Running Auto-Cleanup...", flush=True)
            cutoff_date = datetime.utcnow() - timedelta(days=3)
            
            # Find old briefings for this user
            old_briefings = session.exec(
                select(Briefing).where(
                    Briefing.user_id == target_user_id,
                    Briefing.created_at < cutoff_date
                )
            ).all()
            
            for old_b in old_briefings:
                # Delete from Storage
                if old_b.audio_path and "/" in old_b.audio_path and not old_b.audio_path.startswith("/"):
                     # Heuristic: if it looks like a relative path (user/file), it's in storage
                     delete_file(old_b.audio_path)
                
                # Delete from DB
                session.delete(old_b)
            
            session.commit()
            print(f"DEBUG: Cleanup finished. Removed {len(old_briefings)} old briefings.", flush=True)
            
        except Exception as e:
            logger.error(f"Auto-cleanup failed: {e}")
        
        print("DEBUG: Done.", flush=True)
        return briefing
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        if session:
            session.rollback()
        raise e
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    # Test run
    generate_briefing_content()
