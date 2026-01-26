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

def get_calendar_events(user_id: str):
    """
    Fetches events from ALL calendars for today using DB-stored OAuth tokens.
    """
    session = next(get_session())
    user_settings = session.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    if not user_settings or not user_settings.google_access_token:
        return "Calendar: Not connected. Please connect your Google Calendar in Settings."
    
    try:
        creds = Credentials(
            token=user_settings.google_access_token,
            refresh_token=user_settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                user_settings.google_access_token = creds.token
                user_settings.google_token_expiry = creds.expiry
                session.commit()
                logger.info("Calendar token refreshed successfully")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return "Calendar: Token expired. Please reconnect your Google Calendar."
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Get all calendars
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        end_of_day = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
        
        all_events = []
        
        # Fetch events from each calendar
        for calendar in calendars:
            calendar_id = calendar['id']
            calendar_name = calendar.get('summary', 'Unknown')
            
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=now,
                    timeMax=end_of_day,
                    maxResults=10,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                for event in events_result.get('items', []):
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    event_name = event.get('summary', 'No title')
                    all_events.append({
                        'start': start,
                        'name': event_name,
                        'calendar': calendar_name
                    })
            except Exception as e:
                logger.warning(f"Could not fetch events from {calendar_name}: {e}")
                continue
        
        if not all_events:
            return "No upcoming events for today."
        
        # Sort by start time
        all_events.sort(key=lambda x: x['start'])
        
        event_summary = []
        for event in all_events[:15]:  # Limit to 15 events
            start = event['start']
            if 'T' in start:
                time_part = start.split('T')[1][:5]
                event_summary.append(f"- {time_part}: {event['name']}")
            else:
                event_summary.append(f"- {event['name']} (all day)")
        
        return "Today's Calendar:\n" + "\n".join(event_summary)
        
    except Exception as e:
        logger.error(f"Calendar API Error: {e}")
        return f"Calendar error: Unable to fetch events."
    finally:
        session.close()
