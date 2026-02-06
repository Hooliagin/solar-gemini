from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from database import get_session
from models import UserSettings
from services.notion_service import NotionService
from auth import get_current_user_id
from dependencies import approved_required
import logging

router = APIRouter(prefix="/notion", tags=["notion"], dependencies=[Depends(approved_required)])
logger = logging.getLogger(__name__)
notion_service = NotionService()

@router.get("/authorize")
async def authorize_notion():
    """ 
    Redirects user to Notion OAuth URL.
    Ideally this link is constructed in Frontend, but we can provide a helper.
    """
    return {
        "url": f"https://api.notion.com/v1/oauth/authorize?owner=user&client_id={notion_service.client_id}&redirect_uri={notion_service.redirect_uri}&response_type=code"
    }

@router.get("/callback")
async def notion_callback(code: str, state: str = None, session: Session = Depends(get_session)):
    """
    Handles the redirect from Notion.
    Exchanges code for token and stores it in UserSettings.
    """
    # 1. Exchange Code
    token_data = await notion_service.exchange_code_for_token(code)
    
    if not token_data or "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Notion code")
    
    # 2. Extract Data
    access_token = token_data["access_token"]
    bot_id = token_data.get("bot_id")
    workspace_name = token_data.get("workspace_name", "Notion Workspace")
    
    # 3. Find User (We need a way to know WHICH user this is)
    # Since OAuth redirect comes from Notion, we don't have our bearer token header.
    # We can rely on the 'state' param if we passed the user_id there, 
    # OR we handle this on the frontend:
    #   Frontend receives code -> POSTs to /notion/connect with code + Auth Header
    
    return {
        "message": "Please close this window and return to the app.",
        "code": code, # Send code back to frontend to finish the flow securely
        "workspace_name": workspace_name
    }

@router.post("/connect")
async def connect_notion(
    payload: dict,
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """
    Final step: Frontend sends the code (obtained from callback) to Backend.
    Backend exchanges it and saves to UserSettings.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code required")

    # Exchange Code
    token_data = await notion_service.exchange_code_for_token(code)
    
    if not token_data or "access_token" not in token_data:
         raise HTTPException(status_code=400, detail="Failed to exchange Notion code")

    # Save to User
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    user = session.exec(stmt).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.notion_access_token = token_data["access_token"]
    user.notion_bot_id = token_data.get("bot_id")
    
    # Try to auto-discover a database if not set
    # (Optional: user can select later)
    first_db = await notion_service.search_for_database(user.notion_access_token)
    if first_db:
       user.notion_database_id = first_db
        
    session.add(user)
    session.commit()
    
    return {"status": "success", "workspace": token_data.get("workspace_name")}
