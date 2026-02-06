"""
Admin Router - Hidden user management interface.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, text
from database import get_session
from models import UserSettings, Entry, Briefing, Interest, UserTodo, ResearchTask, Habit, UsedQuote
from auth import get_current_user_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


async def admin_required(user_id: str = Depends(get_current_user_id), session: Session = Depends(get_session)):
    """Dependency to ensure user is an admin."""
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    user = session.exec(stmt).first()
    
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_id


@router.get("/users")
async def list_users(
    _admin_id: str = Depends(admin_required), 
    session: Session = Depends(get_session)
):
    """List all users with basic stats."""
    stmt = select(UserSettings)
    users = session.exec(stmt).all()
    
    result = []
    for user in users:
        # Count entries
        entry_count = session.exec(select(Entry).where(Entry.user_id == user.user_id)).all()
        briefing_count = session.exec(select(Briefing).where(Briefing.user_id == user.user_id)).all()
        
        result.append({
            "user_id": user.user_id,
            "name": user.name,
            "telegram_linked": bool(user.telegram_chat_id),
            "calendar_linked": bool(user.google_access_token),
            "is_admin": user.is_admin,
            "entry_count": len(entry_count),
            "briefing_count": len(briefing_count),
            "created_at": str(user.updated_at) if user.updated_at else None
        })
    
    return result


@router.delete("/users/{target_user_id}")
async def delete_user(
    target_user_id: str,
    _admin_id: str = Depends(admin_required),
    session: Session = Depends(get_session)
):
    """Delete a user and all their associated data."""
    # Verify target user exists
    stmt = select(UserSettings).where(UserSettings.user_id == target_user_id)
    user = session.exec(stmt).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if target_user_id == _admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    logger.warning(f"ADMIN: Deleting user {target_user_id} and all associated data")
    
    # Delete all related data
    session.exec(text("DELETE FROM entry WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM briefing WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM interest WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM usertodo WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM researchtask WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM usedquote WHERE user_id = :uid").bindparams(uid=target_user_id))
    session.exec(text("DELETE FROM habit WHERE user_id = :uid").bindparams(uid=target_user_id))
    
    # Finally delete the user settings
    session.delete(user)
    session.commit()
    
    return {"status": "deleted", "user_id": target_user_id}
