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
    name: Optional[str] = None
    weather_enabled: Optional[bool] = None
    weather_city: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None
    briefing_time: Optional[str] = None
    news_politics: Optional[bool] = None
    news_local: Optional[bool] = None
    news_economy: Optional[bool] = None
    news_tech: Optional[bool] = None
    news_tech: Optional[bool] = None
    news_sports: Optional[bool] = None
    # Reflection Settings
    reflection_time: Optional[str] = None
    reflection_reminder_enabled: Optional[bool] = None
    # Telegram settings
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None

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
    
    # Generate secure 12-char token
    import uuid
    code = uuid.uuid4().hex[:12]
    settings.telegram_link_token = code
    session.add(settings)
    session.commit()
    
    return {"code": code}

class MergeRequest(BaseModel):
    link_code: str

@router.post("/merge")
def merge_account(data: MergeRequest, session: Session = Depends(get_session), target_user_id: str = Depends(get_current_user_id)):
    """
    Merge a Shadow Account (Telegram only) into the current Authenticated Account.
    Used when a Telegram user finally signs up on the Web.
    """
    # 1. Find Shadow User by Link Code
    stmt = select(UserSettings).where(UserSettings.telegram_link_token == data.link_code)
    shadow_user = session.exec(stmt).first()
    
    if not shadow_user:
        raise HTTPException(status_code=404, detail="Invalid link code")
        
    shadow_user_id = shadow_user.user_id
    
    if shadow_user_id == target_user_id:
         return {"status": "same_user", "message": "Already logged in as this user."}

    # 2. Get Target User
    stmt_target = select(UserSettings).where(UserSettings.user_id == target_user_id)
    target_user = session.exec(stmt_target).first()
    
    if not target_user:
        target_user = UserSettings(user_id=target_user_id)
        session.add(target_user)
    
    # 3. Migrate Data
    from models import Entry, Briefing, Interest
    
    # Move Entries
    entries = session.exec(select(Entry).where(Entry.user_id == shadow_user_id)).all()
    for entry in entries:
        entry.user_id = target_user_id
        session.add(entry)
        
    # Move Briefings
    briefings = session.exec(select(Briefing).where(Briefing.user_id == shadow_user_id)).all()
    for briefing in briefings:
        briefing.user_id = target_user_id
        session.add(briefing)
        
    # Move Interests
    interests = session.exec(select(Interest).where(Interest.user_id == shadow_user_id)).all()
    for interest in interests:
        interest.user_id = target_user_id
        session.add(interest)
        
    # Merge Settings (Target takes precedence, but if Target is empty, take Shadow)
    if shadow_user.telegram_enabled:
        target_user.telegram_enabled = True
        target_user.telegram_chat_id = shadow_user.telegram_chat_id
    
    if shadow_user.weather_city and not target_user.weather_city:
        target_user.weather_city = shadow_user.weather_city
        target_user.weather_enabled = shadow_user.weather_enabled
        
    if shadow_user.voice_id and not target_user.voice_id:
        target_user.voice_id = shadow_user.voice_id
        
    # Copy News preferences if not set? No, let's just stick to simplistic merge:
    # Telegram ID is the most important thing to preserve.
    
    # 4. Cleanup Shadow User
    session.delete(shadow_user)
    session.add(target_user)
    
    session.commit()
    
    return {"status": "success", "merged_items": len(entries) + len(briefings)}
