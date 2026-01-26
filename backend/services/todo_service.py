from google import genai
from google.genai import types
from config import settings
from sqlmodel import Session, select
from models import UserTodo
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

# Initialize Gemini Client
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def extract_todos_from_transcript(user_id: str, transcript: str, entry_id: int, session: Session):
    """
    Analyzes the transcript to find actionable tasks.
    Saves them to the database.
    """
    try:
        # 1. Prompt Gemini to extract tasks
        prompt = f"""
        Analyze the following user diary entry/transcript.
        Identify any specific tasks, todos, or reminders the user mentions.
        Examples: 
        - "Remind me to call Mom tomorrow" -> Task: "Call Mom", Due: Tomorrow
        - "I need to buy milk" -> Task: "Buy milk"
        - "I went to the gym" -> NO TASK (just a statement)
        
        Transcript: "{transcript}"
        
        Output JSON ONLY:
        {{
            "todos": [
                {{ "task": "...", "due_in_days": 0 or 1 etc (optional, 0=today, 1=tomorrow) }}
            ]
        }}
        If no todos, return {{ "todos": [] }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                 response_mime_type="application/json"
            )
        )
        
        # 2. Parse Response
        data = json.loads(response.text)
        todos = data.get("todos", [])
        
        extracted_count = 0
        for item in todos:
            task_text = item.get("task")
            if not task_text:
                continue
                
            due_in_days = item.get("due_in_days")
            due_date = None
            if due_in_days is not None:
                due_date = datetime.now() + timedelta(days=due_in_days)
            
            # 3. Save to DB
            todo = UserTodo(
                user_id=user_id,
                task=task_text,
                due_date=due_date,
                source_entry_id=entry_id
            )
            session.add(todo)
            extracted_count += 1
            
        session.commit()
        logger.info(f"Extracted {extracted_count} todos for user {user_id}")
        return extracted_count

    except Exception as e:
        logger.error(f"Error extracting todos: {e}")
        return 0

def get_pending_todos(user_id: str, session: Session) -> list[UserTodo]:
    """Get uncompleted todos for the briefing."""
    statement = select(UserTodo).where(
        UserTodo.user_id == user_id,
        UserTodo.is_completed == False
    )
    return session.exec(statement).all()
