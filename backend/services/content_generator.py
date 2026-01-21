import google.generativeai as genai
from config import settings
from services.calendar_service import get_calendar_events
from services.news_service import fetch_ai_news_summary
from services.tts_service import generate_speech
from database import get_session
from models import Entry, Briefing
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

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
    logger.info("Starting briefing generation...")
    
    # Validation
    if not settings.GOOGLE_API_KEY:
        raise ValueError("Google Gemini API Key (GEMINI_API_KEY) is missing.")

    session = None
    try:
        # 1. Fetch Calendar
        calendar_text = get_calendar_events()
        
        # 2. Fetch User Interests & News
        session = next(get_session())
        
        # Fetch interests
        from models import Interest
        interests = session.query(Interest).all()
        topic_list = [i.topic for i in interests]
        
        # Fetch News based on interests
        news_text = fetch_ai_news_summary(topic_list)
        
        # 3. Fetch yesterday's diary (Last entry from DB)
        last_entry = session.query(Entry).order_by(Entry.id.desc()).first()
        diary_transcript = last_entry.transcript if last_entry else "No diary entry for last night."
        
        # 4. Generate Script using Gemini
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        You are a friendly, professional personal assistant. It is morning.
        Create a morning briefing script for me.
        
        Here is the context:
        
        [YESTERDAY'S DIARY/THOUGHTS]
        {diary_transcript}
        
        [TODAY'S CALENDAR]
        {calendar_text}
        
        [NEWS UPDATES]
        {news_text}
        
        Structure the briefing as follows:
        1. Good morning & quick reflection on yesterday's thoughts.
        2. Overview of today's schedule.
        3. Interesting news snippet.
        4. Motivational closing.
        
        Keep it conversational, warm, and concise (under 3 minutes spoken).
        Do not use markdown formatting like **bold** in the script, as it will be read by TTS. Write it as plain spoken text.
        """
        
        response = model.generate_content(prompt)
        script = response.text
        
        # 5. Generate Audio
        audio_filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        # Ensure audio directory exists
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        generate_speech(script, audio_path_abs)
        
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
