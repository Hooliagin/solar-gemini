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
