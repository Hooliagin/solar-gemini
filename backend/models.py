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
    audio_path: str
    status: str = Field(default="pending") # pending, generated, played

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
    # Google Calendar OAuth tokens
    google_access_token: Optional[str] = Field(default=None)
    google_refresh_token: Optional[str] = Field(default=None)
    google_token_expiry: Optional[datetime] = Field(default=None)
    # News category toggles (predefined)
    news_politics: bool = Field(default=True)
    news_local: bool = Field(default=True)  # Uses weather_city for location
    news_economy: bool = Field(default=False)
    news_tech: bool = Field(default=False)
    news_sports: bool = Field(default=False)
    # Telegram settings
    telegram_chat_id: Optional[str] = Field(default=None)
    telegram_enabled: bool = Field(default=False)
    telegram_link_token: Optional[str] = Field(default=None, index=True) # Code to link via /start <code>
    onboarding_step: Optional[str] = Field(default=None)  # Current step in onboarding flow: name, age, city, voice, news, interests
    updated_at: datetime = Field(default_factory=datetime.utcnow)
