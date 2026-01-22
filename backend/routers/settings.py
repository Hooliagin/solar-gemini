from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from models import UserSettings
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])

class UserSettingsUpdate(BaseModel):
    weather_enabled: Optional[bool] = None
    weather_city: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None

@router.get("/")
def get_settings(session: Session = Depends(get_session)):
    """Get current user settings (or create defaults)."""
    settings = session.query(UserSettings).first()
    if not settings:
        settings = UserSettings()
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings

@router.put("/")
def update_settings(updates: UserSettingsUpdate, session: Session = Depends(get_session)):
    """Update user settings."""
    settings = session.query(UserSettings).first()
    if not settings:
        settings = UserSettings()
        session.add(settings)
    
    if updates.weather_enabled is not None:
        settings.weather_enabled = updates.weather_enabled
    if updates.weather_city is not None:
        settings.weather_city = updates.weather_city
    if updates.voice_id is not None:
        settings.voice_id = updates.voice_id
    if updates.language is not None:
        settings.language = updates.language
    
    session.commit()
    session.refresh(settings)
    return settings
