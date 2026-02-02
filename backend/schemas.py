from pydantic import BaseModel, Field
from typing import List, Optional

# --- TODO EXTRACTION SCHEMAS ---

class TodoItem(BaseModel):
    task: str = Field(description="The concise action item text")
    due_in_days: Optional[int] = Field(description="O if due today, 1 if tomorrow, etc. None if no specific due date.")

class ResearchItem(BaseModel):
    query: str = Field(description="The specific research question to investigate")

class TodoExtractionResponse(BaseModel):
    todos: List[TodoItem] = Field(description="List of actionable tasks extracted from transcript")
    research: List[ResearchItem] = Field(description="List of research requests extracted from transcript")

# --- BRIEFING GENERATION SCHEMAS ---

class AgendaItem(BaseModel):
    start: str = Field(description="Start time strictly in HH:MM format (24h). NEVER use words like 'Morning' or 'Evening'. Example: '07:00', '21:30'.")
    end: Optional[str] = Field(description="End time strictly in HH:MM format.")
    name: str = Field(description="Short, concise event title (Max 2-5 words). Example: 'Sport', 'Deep Work', 'Lunch'.")
    type: str = Field(description="Type of event: 'fixed' (from calendar) or 'suggestion' (from AI/Habits)")

class QuoteItem(BaseModel):
    text: str = Field(description="The full quote text")
    author: str = Field(description="The author of the quote")

class BriefingResponse(BaseModel):
    script_content: str = Field(description="The COMPLETE spoken briefing text (script). Must be natural, conversational German. NO Markdown.")
    quotes: List[QuoteItem] = Field(description="The two quotes selected/used in the script")
    final_agenda: List[AgendaItem] = Field(description="The final agenda including ALL events mentioned in the script. If you mention it, it MUST be here.")

