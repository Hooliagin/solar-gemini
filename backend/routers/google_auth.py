from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from database import get_session
from models import UserSettings
from config import settings
from datetime import datetime
import os

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events', # Read/Write events
    'https://www.googleapis.com/auth/calendar.readonly' # List calendars
]
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://daily-manager-backend.onrender.com/auth/google/callback")

def get_flow():
    """Create OAuth flow with client credentials."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow

from auth import get_current_user_id
from sqlmodel import select
from typing import Optional

@router.get("/google")
def google_auth(user_id: Optional[str] = None):
    """Initiate Google OAuth flow - redirects user to Google login.
    
    user_id can be passed as query param for direct browser redirects.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required as query parameter")
    
    flow = get_flow()
    # Pass user_id as state to identify user in callback
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',  # Force consent to get refresh token
        state=user_id 
    )
    return RedirectResponse(authorization_url)

@router.get("/google/callback")
def google_callback(state: str, code: str = None, error: str = None, session: Session = Depends(get_session)):
    """Handle OAuth callback from Google."""
    # state contains the user_id we passed in /google
    if error:
        return RedirectResponse(f"https://daily-manager-frontend.onrender.com/?calendar_error={error}")
    
    if not code:
        return RedirectResponse("https://daily-manager-frontend.onrender.com/?calendar_error=no_code")
    
    user_id = state
    
    try:
        # Relax scope validation because Google returns all granted scopes (e.g. readonly + events)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get or create user settings for this SPECIFIC user
        statement = select(UserSettings).where(UserSettings.user_id == user_id)
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            user_settings = UserSettings(user_id=user_id)
            session.add(user_settings)
        
        # Store tokens
        user_settings.google_access_token = credentials.token
        user_settings.google_refresh_token = credentials.refresh_token
        user_settings.google_token_expiry = credentials.expiry
        user_settings.updated_at = datetime.utcnow()
        
        session.add(user_settings)
        session.commit()
        
        # Redirect to frontend with success
        return RedirectResponse("https://daily-manager-frontend.onrender.com/?calendar_connected=true")
        
    except Exception as e:
        print(f"Google OAuth Error: {e}")
        return RedirectResponse(f"https://daily-manager-frontend.onrender.com/?calendar_error=auth_failed")

@router.get("/google/status")
def google_status(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Check if Google Calendar is connected."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    user_settings = session.exec(statement).first()
    
    if not user_settings or not user_settings.google_access_token:
        return {"connected": False}
    
    # Check if token is expired
    if user_settings.google_token_expiry and user_settings.google_token_expiry < datetime.utcnow():
        # Token expired, might still work if we have refresh token
        return {"connected": True, "expired": True, "has_refresh": bool(user_settings.google_refresh_token)}
    
    return {"connected": True, "expired": False}

@router.post("/google/disconnect")
def google_disconnect(session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)):
    """Disconnect Google Calendar."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    user_settings = session.exec(statement).first()
    
    if user_settings:
        user_settings.google_access_token = None
        user_settings.google_refresh_token = None
        user_settings.google_token_expiry = None
        session.add(user_settings)
        session.commit()
    return {"status": "disconnected"}
