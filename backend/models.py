from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)  # Supabase Auth User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    audio_path: str
    transcript: Optional[str] = None
    language: Optional[str] = Field(default=None)  # Detected language (e.g., "de", "en")
    summary: Optional[str] = None

class Briefing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)  # Supabase Auth User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: datetime
    script_content: str
    calendar_events: Optional[str] = Field(default=None) # JSON encoded list of events
    audio_path: str
    status: str = Field(default="pending") # pending, generated, played
    type: str = Field(default="daily", index=True) # daily, weekly

class Interest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)  # Supabase Auth User ID
    topic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(unique=True, index=True)  # Supabase Auth User ID
    # User profile
    name: Optional[str] = Field(default=None)
    age: Optional[int] = Field(default=None)
    # Weather settings
    weather_enabled: bool = Field(default=True)
    weather_city: str = Field(default="Berlin")
    # Voice settings
    voice_id: str = Field(default="alloy")  # OpenAI TTS voice
    # Language preference
    language: str = Field(default="de")
    # Briefing schedule
    briefing_time: str = Field(default="07:00")  # Time for daily briefing (HH:MM format)
    # Google Calendar OAuth tokens
    google_access_token: Optional[str] = Field(default=None)
    google_refresh_token: Optional[str] = Field(default=None)
    google_token_expiry: Optional[datetime] = Field(default=None)
    # Selected Calendar IDs (JSON list or comma-separated)
    selected_calendars: Optional[str] = Field(default=None)
    # News category toggles (predefined)
    news_politics: bool = Field(default=True)
    news_local: bool = Field(default=True)  # Uses weather_city for location
    news_economy: bool = Field(default=False)
    news_tech: bool = Field(default=False)
    news_sports: bool = Field(default=False)
    # Telegram settings
    telegram_chat_id: Optional[str] = Field(default=None, sa_column_kwargs={"unique": True})
    telegram_enabled: bool = Field(default=False)
    telegram_link_token: Optional[str] = Field(default=None, index=True) # Code to link via /start <code>
    # Reflection Reminder settings
    reflection_time: str = Field(default="19:00") # Time for reflection reminder (HH:MM)
    reflection_reminder_enabled: bool = Field(default=True)

    onboarding_step: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
class UserTodo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    task: str  # The actual todo text
    due_date: Optional[datetime] = None # If user says "tomorrow"
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
class ResearchTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    query: str # The search query/topic (e.g. "Solar ETF Performance")
    status: str = Field(default="pending") # pending, done
    result_summary: Optional[str] = None # The summary found by the agent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_entry_id: Optional[int] = None

class UsedQuote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    quote_id: str = Field(index=True) # Hash of author:quote
    quote_text_snippet: str # Stored just for debugging reference
    used_at: datetime = Field(default_factory=datetime.utcnow)

class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    name: str  # e.g. "Morning Light"
    description: Optional[str] = None  # e.g. "Go outside for 10 min"
    preferred_time: str = Field(default="any")  # morning, afternoon, evening, any
    duration_minutes: int = Field(default=30)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
