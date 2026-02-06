from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from auth import get_current_user_id
from models import UserSettings

async def approved_required(
    user_id: str = Depends(get_current_user_id), 
    session: Session = Depends(get_session)
) -> str:
    """
    Dependency that ensures the user is approved by an admin.
    Returns user_id if approved, raises 403 if not.
    """
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    user = session.exec(stmt).first()
    
    if not user:
        # User doesn't exist yet (haven't hit settings endpoint?)
        # Or just auto-create? Better to raise 403 if they don't exist in our DB yet.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Account not initialized"
        )
        
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Account pending approval"
        )
        
    return user_id
