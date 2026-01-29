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

def get_calendar_events(user_id: str) -> list[dict]:
    """
    Fetches events from ALL calendars for today using DB-stored OAuth tokens.
    Returns a list of event dictionaries.
    """
    session = next(get_session())
    user_settings = session.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    if not user_settings or not user_settings.google_access_token:
        logger.warning("Calendar: Not connected.")
        return []
    
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
                return []
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Get all calendars
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        from zoneinfo import ZoneInfo
        
        # Force German Timezone for "Today" calculation
        tz = ZoneInfo("Europe/Berlin")
        now_local = datetime.datetime.now(tz)
        
        start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_local = now_local.replace(hour=23, minute=59, second=59, microsecond=0)
        
        time_min = start_of_day.isoformat()
        time_max = end_of_day_local.isoformat()
        
        all_events = []
        
        # Fetch events from each calendar
        for calendar in calendars:
            calendar_id = calendar['id']
            calendar_name = calendar.get('summary', 'Unknown')
            
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=10,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                for event in events_result.get('items', []):
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    # Extract End Time
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    # Normalize start to just ISO string without timezone offset if needed, or keep as is
                    
                    event_name = event.get('summary', 'No title')
                    all_events.append({
                        'start': start,
                        'end': end,
                        'name': event_name,
                        'calendar': calendar_name,
                        'id': event.get('id')
                    })
            except Exception as e:
                logger.warning(f"Could not fetch events from {calendar_name}: {e}")
                continue
        
        # Sort by start time
        all_events.sort(key=lambda x: x['start'])
        return all_events
        
    except Exception as e:
        logger.error(f"Calendar API Error: {e}")
        return []
    finally:
        session.close()

def format_events_text(events: list[dict]) -> str:
    """Formats the structured event list into a string for the LLM prompt."""
    if not events:
        return "No upcoming events for today."
    
    event_summary = []
    for event in events[:15]:  # Limit to 15 events
        start = event['start']
        end = event.get('end', '')
        
        time_str = ""
        if 'T' in start:
            start_time = start.split('T')[1][:5]
            end_time = end.split('T')[1][:5] if 'T' in end else "?"
            time_str = f"{start_time}-{end_time}"
        else:
            time_str = "All Day"
            
        event_summary.append(f"- {time_str}: {event['name']}")
    
    return "Today's Calendar:\n" + "\n".join(event_summary)

def create_calendar_event(user_id: str, event_data: dict) -> bool:
    """
    Creates a new event in the user's primary calendar.
    event_data expected: {'name': str, 'start': iso_str, 'end': iso_str, 'description': str}
    """
    session = next(get_session())
    user_settings = session.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    if not user_settings or not user_settings.google_access_token:
        logger.warning("Calendar: Not connected for write.")
        return False
        
    try:
        creds = Credentials(
            token=user_settings.google_access_token,
            refresh_token=user_settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        
        # Auto-refresh if needed logic (same as fetch)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            user_settings.google_access_token = creds.token
            session.commit()
            
        service = build('calendar', 'v3', credentials=creds)
        
        # Construct body
        body = {
            'summary': event_data['name'],
            'description': event_data.get('description', 'Created by Daily Manager AI'),
            'start': {
                'dateTime': event_data['start'],
                'timeZone': 'Europe/Berlin', # Force Berlin for simplicity? Or infer?
            },
            'end': {
                'dateTime': event_data['end'],
                'timeZone': 'Europe/Berlin',
            },
        }
        
        service.events().insert(calendarId='primary', body=body).execute()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return False
    finally:
        session.close()
