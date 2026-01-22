from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import UserSettings
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user_id
import random
import string

router = APIRouter(prefix="/settings", tags=["settings"])

class UserSettingsUpdate(BaseModel):
    weather_enabled: Optional[bool] = None
    weather_city: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None
    news_politics: Optional[bool] = None
    news_local: Optional[bool] = None
    news_economy: Optional[bool] = None
    news_tech: Optional[bool] = None
    news_sports: Optional[bool] = None

@router.get("/")
def get_settings(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Get settings for the current user."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    settings = session.exec(statement).first()
    
    if not settings:
        # Create default settings for new user
        settings = UserSettings(user_id=user_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    
    return settings

@router.put("/")
def update_settings(updates: UserSettingsUpdate, session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Update user settings."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    settings = session.exec(statement).first()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        session.add(settings)
    
    # Update fields dynamically
    updates_dict = updates.model_dump(exclude_unset=True)
    for key, value in updates_dict.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
            
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings

@router.post("/telegram/link-code")
def generate_telegram_link_code(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Generate a short code to link Telegram account."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    settings = session.exec(statement).first()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        session.add(settings)
    
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    settings.telegram_link_token = code
    session.add(settings)
    session.commit()
    
    return {"code": code}
