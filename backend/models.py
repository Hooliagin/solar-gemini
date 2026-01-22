from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    audio_path: str
    transcript: Optional[str] = None
    summary: Optional[str] = None

class Briefing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: datetime
    script_content: str
    audio_path: str
    status: str = Field(default="pending") # pending, generated, played

class Interest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Weather settings
    weather_enabled: bool = Field(default=True)
    weather_city: str = Field(default="Berlin")
    # Voice settings (for Phase 3)
    voice_id: str = Field(default="alloy")  # OpenAI TTS voice
    # Language preference (for Phase 2)
    language: str = Field(default="de")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
