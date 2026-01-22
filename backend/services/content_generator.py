import google.generativeai as genai
from config import settings
from services.calendar_service import get_calendar_events
from services.news_service import fetch_ai_news_summary
from services.weather_service import get_weather_briefing
from services.tts_service import generate_speech
from database import get_session
from models import Entry, Briefing, UserSettings
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Configure Gemini (moved inside function to handle missing key gracefully)
# genai.configure(api_key=settings.GOOGLE_API_KEY)

def generate_briefing_content():
    """
    Orchestrates the creation of the morning briefing.
    1. Fetch yesterday's diary (Entry).
    2. Fetch today's Calender.
    3. Fetch News/Topics.
    4. Generate Script (Gemini).
    5. Generate Audio (OpenAI TTS).
    6. Save Briefing record.
    """
    import sys
    print("DEBUG: Starting briefing generation...", flush=True)
    logger.info("Starting briefing generation...")
    
    # Validation
    if not settings.GOOGLE_API_KEY:
        print("DEBUG: Missing Google API Key", flush=True)
        raise ValueError("Google Gemini API Key (GEMINI_API_KEY) is missing.")

    # Configure Gemini
    print("DEBUG: Configuring Gemini...", flush=True)
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    session = None
    try:
        # 1. Fetch Calendar
        print("DEBUG: Fetching Calendar...", flush=True)
        calendar_text = get_calendar_events()
        print(f"DEBUG: Calendar Fetched ({len(calendar_text)} chars).", flush=True)
        
        # 2. Fetch User Interests & News
        print("DEBUG: Getting DB Session...", flush=True)
        session = next(get_session())
        
        # Fetch interests
        print("DEBUG: Querying Interests...", flush=True)
        from models import Interest
        interests = session.query(Interest).all()
        topic_list = [i.topic for i in interests]
        print(f"DEBUG: Found topics: {topic_list}", flush=True)
        
        # Fetch News based on interests
        print("DEBUG: Fetching News...", flush=True)
        news_text = fetch_ai_news_summary(topic_list)
        print(f"DEBUG: News Fetched ({len(news_text)} chars).", flush=True)
        
        # 3. Fetch yesterday's diary (Last entry from DB)
        print("DEBUG: Fetching last diary entry...", flush=True)
        last_entry = session.query(Entry).order_by(Entry.id.desc()).first()
        diary_transcript = last_entry.transcript if last_entry else "No diary entry for last night."
        detected_language = last_entry.language if last_entry and last_entry.language else "de"  # Default to German
        print(f"DEBUG: Detected language: {detected_language}", flush=True)
        
        # 4. Fetch Weather (if enabled)
        print("DEBUG: Checking Weather Settings...", flush=True)
        user_settings = session.query(UserSettings).first()
        weather_text = ""
        if user_settings and user_settings.weather_enabled:
            print(f"DEBUG: Fetching Weather for {user_settings.weather_city}...", flush=True)
            weather_text = get_weather_briefing(user_settings.weather_city)
            print(f"DEBUG: Weather Fetched ({len(weather_text)} chars).", flush=True)
        elif not user_settings:
            # Create default settings if none exist
            print("DEBUG: Creating default UserSettings...", flush=True)
            user_settings = UserSettings()
            session.add(user_settings)
            session.commit()
            weather_text = get_weather_briefing(user_settings.weather_city)
        
        # 4. Generate Script using Gemini
        print("DEBUG: Initializing Gemini Model...", flush=True)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Determine language instruction for Gemini
        language_instruction = "Respond in German (Deutsch)." if detected_language == "de" else f"Respond in English."
        if detected_language not in ["de", "en"]:
            language_instruction = f"Respond in the same language as the diary entry (detected: {detected_language})."
        
        prompt = f"""
        You are a friendly, professional personal assistant. It is morning.
        Create a morning briefing script for me.
        
        **IMPORTANT: {language_instruction}**
        
        Here is the context:
        
        [YESTERDAY'S DIARY/THOUGHTS]
        {diary_transcript}
        
        [TODAY'S CALENDAR]
        {calendar_text}
        
        [WEATHER]
        {weather_text if weather_text else "Weather data not available."}
        
        [NEWS UPDATES]
        {news_text}
        
        Structure the briefing as follows:
        1. Good morning & quick reflection on yesterday's thoughts.
        2. Overview of today's schedule.
        3. Weather update with clothing recommendation.
        4. Interesting news snippet.
        5. Motivational closing.
        
        Keep it conversational, warm, and concise (under 3 minutes spoken).
        Do not use markdown formatting like **bold** in the script, as it will be read by TTS. Write it as plain spoken text.
        """
        
        print("DEBUG: Generating Content with Gemini...", flush=True)
        response = model.generate_content(prompt)
        print("DEBUG: Gemini Response Received.", flush=True)
        script = response.text
        
        # 5. Generate Audio
        print("DEBUG: Generating Audio (TTS)...", flush=True)
        audio_filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        # Ensure audio directory exists
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        generate_speech(script, audio_path_abs, language=detected_language)
        print(f"DEBUG: Audio saved to {audio_path_abs} (lang: {detected_language})", flush=True)
        
        # 6. Save Briefing to DB
        briefing = Briefing(
            scheduled_for=datetime.now(),
            script_content=script,
            audio_path=audio_path_abs,
            status="generated"
        )
        session.add(briefing)
        session.commit()
        
        logger.info(f"Briefing generated successfully: {audio_path_abs}")
        print("DEBUG: Briefing saved to DB. Done.", flush=True)
        return briefing
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        if session:
            session.rollback()
        raise e # Re-raise to let the router handle the error response
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    # Test run
    generate_briefing_content()
