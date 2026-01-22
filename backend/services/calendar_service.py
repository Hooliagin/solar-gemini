import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import settings
from database import get_session
from models import UserSettings
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_events():
    """
    Fetches the upcoming 10 events for today using DB-stored OAuth tokens.
    """
    # Get tokens from database
    session = next(get_session())
    user_settings = session.query(UserSettings).first()
    
    if not user_settings or not user_settings.google_access_token:
        return "Calendar: Not connected. Please connect your Google Calendar in Settings."
    
    try:
        # Build credentials from stored tokens
        creds = Credentials(
            token=user_settings.google_access_token,
            refresh_token=user_settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Update stored tokens
                user_settings.google_access_token = creds.token
                user_settings.google_token_expiry = creds.expiry
                session.commit()
                logger.info("Calendar token refreshed successfully")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return "Calendar: Token expired. Please reconnect your Google Calendar."
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get today's events
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        end_of_day = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_of_day,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events for today."
        
        event_summary = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Format time nicely
            if 'T' in start:
                time_part = start.split('T')[1][:5]
                event_summary.append(f"- {time_part}: {event['summary']}")
            else:
                event_summary.append(f"- {event['summary']} (all day)")
        
        return "Today's Calendar:\n" + "\n".join(event_summary)
        
    except Exception as e:
        logger.error(f"Calendar API Error: {e}")
        return f"Calendar error: Unable to fetch events."
    finally:
        session.close()
