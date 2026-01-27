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
from datetime import datetime
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
        
        # Fetch ALL news (predefined categories + custom topics)
        print("DEBUG: Fetching News (categories + custom)...", flush=True)
        from services.news_service import fetch_all_news
        
        all_news = fetch_all_news(user_settings, topic_list)
        print(f"DEBUG: All News Fetched ({len(all_news)} chars).", flush=True)
        
        # 3. Fetch yesterday's diary (Last entry from DB for THIS USER)
        print("DEBUG: Fetching last diary entry...", flush=True)
        statement = select(Entry).where(Entry.user_id == target_user_id).order_by(Entry.id.desc())
        last_entry = session.exec(statement).first()
        
        diary_transcript = last_entry.transcript if last_entry else "No diary entry for last night."
        detected_language = last_entry.language if last_entry and last_entry.language else "de"  # Default to German
        print(f"DEBUG: Detected language: {detected_language}", flush=True)
        
        # 4. Fetch Weather (if enabled)
        print("DEBUG: Checking Weather Settings...", flush=True)
        weather_text = ""
        if user_settings.weather_enabled:
            print(f"DEBUG: Fetching Weather for {user_settings.weather_city}...", flush=True)
            weather_text = get_weather_briefing(user_settings.weather_city)
            print(f"DEBUG: Weather Fetched ({len(weather_text)} chars).", flush=True)
        
        # 4. Generate Script using Gemini
        print("DEBUG: Initializing Gemini Model...", flush=True)
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # Determine language instruction for Gemini
        language_instruction = "Respond in German (Deutsch)." if detected_language == "de" else f"Respond in English."
        if detected_language not in ["de", "en"]:
            language_instruction = f"Respond in the same language as the diary entry (detected: {detected_language})."
        
        # Get user's name for personalized greeting
        user_name = user_settings.name if user_settings.name else ""
        greeting_instruction = f"Address the user by name: '{user_name}'" if user_name else "Use a friendly greeting"
        
        # 3b. Fetch Pending Todos
        print("DEBUG: Fetching Pending Todos...", flush=True)
        from services.todo_service import get_pending_todos, get_pending_research
        todos = get_pending_todos(target_user_id, session)
        todo_list_text = "\n".join([f"- {t.task} (Due: {t.due_date.strftime('%Y-%m-%d') if t.due_date else 'Anytime'})" for t in todos])
        if not todo_list_text:
            todo_list_text = "No pending tasks."
            
        # 3c. Perform Pending Research (JIT)
        print("DEBUG: Checking for Research Tasks...", flush=True)
        research_tasks = get_pending_research(target_user_id, session)
        research_results_text = ""
        
        if research_tasks:
            from services.research_service import perform_research_grounding
            print(f"DEBUG: Found {len(research_tasks)} research tasks. Executing...", flush=True)
            
            for task in research_tasks:
                print(f"DEBUG: Researching '{task.query}'...", flush=True)
                summary = perform_research_grounding(task.query)
                
                research_results_text += f"\n[REQUEST: {task.query}]\nRESULT: {summary}\n"
                
                # Mark as done
                task.status = "done"
                task.result_summary = summary
                session.add(task)
            
            session.commit()
        else:
            research_results_text = "No research requests."

        prompt = f"""
        You are a friendly, professional personal assistant. It is morning.
        Create a DETAILED morning briefing script for the user.
        
        **IMPORTANT: {language_instruction}**
        **GREETING: {greeting_instruction}**
        
        **CRITICAL TTS OPTIMIZATION RULES:**
        - NEVER use Markdown formatting (no **, -, #, _, `, etc.)
        - Write EVERYTHING as natural spoken text
        - Spell out ALL numbers as words (e.g., "fünf" not "5", "zehn Uhr" not "10:00")
        - Use full words, NEVER abbreviations (e.g., "zum Beispiel" not "z.B.", "das heißt" not "d.h.")
        - Write times in spoken format (e.g., "zehn Uhr dreißig" not "10:30")
        - Use natural pauses with punctuation (commas, periods)
        - Write dates in full spoken form (e.g., "dreiundzwanzigster Januar" not "23.01.")
        - **GRAMMAR CHECK**: Ensure perfect German grammar. Do NOT make mistakes like 'bist geschlafen'. Use 'hast geschlafen'.
        
        Here is the context:
        
        [YESTERDAY'S DIARY/THOUGHTS]
        {diary_transcript}

        [USER TODOS / REMINDERS]
        {todo_list_text}
        
        [RESEARCH RESULTS (ANSWERS TO USER QUESTIONS)]
        {research_results_text}
        
        [TODAY'S CALENDAR]
        {calendar_text}
        
        [WEATHER]
        {weather_text if weather_text else "Weather data not available."}
        
        [NEWS & TOPICS]
        {all_news}
        
        **CRITICAL: FLOW TEXT ONLY (FLIESSTEXT)**
        - **ABSOLUTELY NO HEADLINES**.
        - The text must sound like a continuous, coherent radio moderation.
        
        **STRUCTURE (Internal Guide):**
        1. **Warm Greeting**: Personal and friendly.
        2. **Deep Retrospective (Yesterday)**:
           - Analyze the diary entry: What did the user ACHIEVE? What was left UNFINISHED?
           - Be specific and praising about achievements.
           - Mention unfinished things gently as context for today.
        3. **Resolutions & Intentions**:
           - Based on yesterday, formulate 1-2 clear intentions/mottos for today.
           - Example: "Yesterday was stressful, so today we focus on potential."
        4. **The Plan (Calendar & Todos)**:
           - **Step A (The Hard Landscape)**: Mention the fixed appointments clearly (Time + Event). Don't skip them.
           - **Step B (The Gaps)**: Look for free slots between appointments.
           - **Step C (Integration)**: Suggest when to do the [USER TODOS] in those gaps.
           - Example: "You have meetings until 2 PM, but a free block afterwards—perfect to finally call Mom (from your todos)."
        5. **Research Answers (If any)**:
           - If there are [RESEARCH RESULTS], present them now.
           - Say: "You asked me to look up X. Here is what I found..."
        6. **News (The Meat)**: 2-3 topics, transitioned smoothly.
        7. **Weather**: Quick check.
        8. **Creative Closing**: END with a unique Quote/Wisdom.

        
        **STYLE**: Energetic but thoughtful. Like a mentor and a friend.
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
        audio_filename = f"briefing_{target_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        # Ensure audio directory exists
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        # Get user's preferred voice from settings
        user_voice = user_settings.voice_id if user_settings else None
        generate_speech(script, audio_path_abs, language=detected_language, voice_override=user_voice)
        print(f"DEBUG: Audio saved to {audio_path_abs} (lang: {detected_language}, voice: {user_voice})", flush=True)
        
        # 6. Save Briefing to DB
        briefing = Briefing(
            user_id=target_user_id,
            scheduled_for=datetime.now(),
            script_content=script,
            audio_path=audio_path_abs,
            status="generated"
        )
        session.add(briefing)
        session.commit()
        session.refresh(briefing)
        
        logger.info(f"Briefing generated successfully: {audio_path_abs}")
        print("DEBUG: Briefing saved to DB.", flush=True)
        
        # 7. (Removed) Sending is now handled by the caller (scheduler or router)
        # to avoid asyncio event loop conflicts.
        
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
