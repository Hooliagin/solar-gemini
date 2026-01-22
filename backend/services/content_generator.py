from google import genai
from google.genai import types
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

    # Gemini client will be initialized later when needed
    print("DEBUG: API Key validated.", flush=True)

    session = None
    try:
        # 1. Fetch Calendar
        print("DEBUG: Fetching Calendar...", flush=True)
        calendar_text = get_calendar_events()
        print(f"DEBUG: Calendar Fetched ({len(calendar_text)} chars).", flush=True)
        
        # 2. Fetch User Interests & News
        print("DEBUG: Getting DB Session...", flush=True)
        session = next(get_session())
        
        # Get user settings first (needed for news categories)
        user_settings = session.query(UserSettings).first()
        
        # Fetch custom interests
        print("DEBUG: Querying Interests...", flush=True)
        from models import Interest
        interests = session.query(Interest).all()
        topic_list = [i.topic for i in interests]
        print(f"DEBUG: Found custom topics: {topic_list}", flush=True)
        
        # Fetch ALL news (predefined categories + custom topics)
        print("DEBUG: Fetching News (categories + custom)...", flush=True)
        from services.news_service import fetch_all_news
        
        all_news = fetch_all_news(user_settings, topic_list)
        print(f"DEBUG: All News Fetched ({len(all_news)} chars).", flush=True)
        
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
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # Determine language instruction for Gemini
        language_instruction = "Respond in German (Deutsch)." if detected_language == "de" else f"Respond in English."
        if detected_language not in ["de", "en"]:
            language_instruction = f"Respond in the same language as the diary entry (detected: {detected_language})."
        
        prompt = f"""
        You are a friendly, professional personal assistant. It is morning.
        Create a DETAILED morning briefing script for me.
        
        **IMPORTANT: {language_instruction}**
        
        Here is the context:
        
        [YESTERDAY'S DIARY/THOUGHTS]
        {diary_transcript}
        
        [TODAY'S CALENDAR]
        {calendar_text}
        
        [WEATHER]
        {weather_text if weather_text else "Weather data not available."}
        
        [NEWS & TOPICS]
        {all_news}
        
        Structure the briefing as follows:
        1. Warm, personal good morning greeting.
        2. Thoughtful reflection on yesterday's diary entry - pick up on emotions or plans mentioned, give supportive advice.
        3. Detailed overview of today's schedule - mention each event with times and any preparation tips.
        4. Weather update with specific clothing and planning recommendations.
        5. NEWS SECTION (THIS IS IMPORTANT - spend time on this):
           - Go through EACH news topic in detail
           - For each topic, provide 2-3 sentences of context and analysis
           - Make it informative and engaging
        6. Motivational closing with a positive thought for the day.
        
        IMPORTANT:
        - Make the briefing DETAILED and SUBSTANTIAL (aim for 5-7 minutes spoken)
        - The news section should be the longest part
        - Be conversational and warm, like a personal assistant who knows me
        - Do not use markdown formatting like **bold**, as it will be read by TTS
        - Write it as natural spoken text
        """
        
        print("DEBUG: Generating Content with Gemini...", flush=True)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        print("DEBUG: Gemini Response Received.", flush=True)
        script = response.text
        
        # 5. Generate Audio
        print("DEBUG: Generating Audio (TTS)...", flush=True)
        audio_filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        # Ensure audio directory exists
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        # Get user's preferred voice from settings
        user_voice = user_settings.voice_id if user_settings else None
        generate_speech(script, audio_path_abs, language=detected_language, voice_override=user_voice)
        print(f"DEBUG: Audio saved to {audio_path_abs} (lang: {detected_language}, voice: {user_voice})", flush=True)
        
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
        print("DEBUG: Briefing saved to DB.", flush=True)
        
        # 7. Send to Telegram if enabled
        if user_settings and user_settings.telegram_enabled and user_settings.telegram_chat_id:
            try:
                print(f"DEBUG: Sending briefing to Telegram (chat_id: {user_settings.telegram_chat_id})...", flush=True)
                from services.telegram_service import send_briefing_audio
                import asyncio
                
                caption = f"🌅 Dein Morgen-Briefing für {datetime.now().strftime('%d.%m.%Y')}"
                success = asyncio.run(send_briefing_audio(
                    chat_id=user_settings.telegram_chat_id,
                    audio_path=audio_path_abs,
                    caption=caption
                ))
                
                if success:
                    print("DEBUG: Briefing sent to Telegram successfully!", flush=True)
                else:
                    print("DEBUG: Failed to send briefing to Telegram.", flush=True)
                    
            except Exception as telegram_error:
                logger.error(f"Error sending to Telegram: {telegram_error}")
                print(f"DEBUG: Telegram error: {telegram_error}", flush=True)
        
        print("DEBUG: Done.", flush=True)
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
