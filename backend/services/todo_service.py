from google import genai
from google.genai import types
from config import settings
from sqlmodel import Session, select
from models import UserTodo, ResearchTask
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

# Initialize Gemini Client lazily inside functions
# client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def extract_todos_from_transcript(user_id: str, transcript: str, entry_id: int, session: Session):
    """
    Analyzes the transcript to find actionable tasks AND research requests.
    Saves them to the database.
    """
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        # 1. Prompt Gemini to extract tasks AND research
        prompt = f"""
        Analyze the following user diary entry/transcript.
        Identify:
        1. Specific tasks/todos (Actionable items for the user).
        2. Research/Information requests (Things the user wants YOU/The AI to find out).
        
        Examples: 
        - "Remind me to call Mom tomorrow" -> Todo: "Call Mom", Due: Tomorrow
        - "I wonder what the stock price of Apple is" -> Research: "Current Apple stock price"
        - "Find out who won the game last night" -> Research: "Winner of game last night"
        - "I need to buy milk" -> Todo: "Buy milk"
        
        Transcript: "{transcript}"
        
        Output JSON ONLY:
        {{
            "todos": [
                {{ "task": "...", "due_in_days": 0 or 1 etc (optional) }}
            ],
            "research": [
                {{ "query": "..." }}
            ]
        }}
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
        research = data.get("research", [])
        
        extracted_count = 0
        
        # Save Todos
        for item in todos:
            task_text = item.get("task")
            if not task_text: continue
            due_in_days = item.get("due_in_days")
            due_date = datetime.now() + timedelta(days=due_in_days) if due_in_days is not None else None
            
            session.add(UserTodo(user_id=user_id, task=task_text, due_date=due_date, source_entry_id=entry_id))
            extracted_count += 1
            
        # Save Research Tasks
        for item in research:
            query = item.get("query")
            if not query: continue
            
            session.add(ResearchTask(user_id=user_id, query=query, source_entry_id=entry_id))
            extracted_count += 1
            
        session.commit()
        logger.info(f"Extracted {extracted_count} items (Todos+Research) for user {user_id}")
        return extracted_count

    except Exception as e:
        logger.error(f"Error extracting items: {e}")
        return 0

def get_pending_todos(user_id: str, session: Session) -> list[UserTodo]:
    """Get uncompleted todos from the last 24 hours (Strict: New Day = New List)."""
    cutoff_date = datetime.utcnow() - timedelta(hours=24)
    return session.exec(
        select(UserTodo)
        .where(
            UserTodo.user_id == user_id, 
            UserTodo.is_completed == False,
            UserTodo.created_at >= cutoff_date
        )
    ).all()

def get_pending_research(user_id: str, session: Session) -> list[ResearchTask]:
    """Get pending research tasks."""
    return session.exec(select(ResearchTask).where(ResearchTask.user_id == user_id, ResearchTask.status == "pending")).all()
