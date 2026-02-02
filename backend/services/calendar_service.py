import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import settings
from database import get_session
from models import UserSettings
import logging

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]

def get_calendar_events(user_id: str, days: int = 1) -> list[dict]:
    """
    Fetches events from ALL calendars for the specified number of days (default 1).
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
        # End of period (1 day or 7 days)
        end_date = now_local + datetime.timedelta(days=days-1)
        end_of_period = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
        
        time_min = start_of_day.isoformat()
        time_max = end_of_period.isoformat()
        
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
        
        # STRICT PYTHON-SIDE FILTERING
        # Google API 'timeMin' is inclusive, so it might return events ending exactly at 00:00 (like yesterday's all-day events).
        # We must filter those out.
        filtered_events = []
        for e in all_events:
            # Parse start/end to comparable datetimes
            try:
                e_start_str = e['start']
                e_end_str = e.get('end')
                
                # Handle All-Day dates (YYYY-MM-DD - no T)
                if 'T' not in e_start_str:
                     e_start_dt = datetime.datetime.fromisoformat(e_start_str).replace(tzinfo=tz)
                     # For end date of all-day, usually YYYY-MM-DD (exclusive)
                     if e_end_str and 'T' not in e_end_str:
                         e_end_dt = datetime.datetime.fromisoformat(e_end_str).replace(tzinfo=tz)
                     else:
                         e_end_dt = e_start_dt + datetime.timedelta(days=1)
                else:
                    # ISO Format
                    e_start_dt = datetime.datetime.fromisoformat(e_start_str)
                    e_end_dt = datetime.datetime.fromisoformat(e_end_str) if e_end_str else e_start_dt
                
                # Check Overlap: Event End must be > Start of Day (Strictly Greater)
                # If Event End == Start of Day, it ended exactly when "Today" began (e.g. Yesterday All Day).
                if e_end_dt > start_of_day:
                    filtered_events.append(e)
                else:
                    logger.info(f"Filtered out past event: {e['name']} (Ended: {e_end_dt} <= {start_of_day})")

            except Exception as parse_err:
                logger.warning(f"Failed to parse event dates for filter: {parse_err}. Keeping event.")
                filtered_events.append(e) # Keep if unsafe to drop
        
        return filtered_events
        
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
        
        # Helper to ensure RFC3339 format (YYYY-MM-DDTHH:MM:SS)
        def normalize_iso(iso_str):
            if not iso_str: return None
            
            # If string is just HH:MM or HH:MM:SS, attach today's date
            if len(iso_str) <= 8 and ':' in iso_str:
                 from zoneinfo import ZoneInfo
                 berlin = ZoneInfo("Europe/Berlin")
                 today = datetime.datetime.now(berlin).date().isoformat()
                 iso_str = f"{today}T{iso_str}"

            try:
                dt = datetime.datetime.fromisoformat(iso_str)
                return dt.isoformat(timespec='seconds') 
            except ValueError:
                # If it still fails, try forcing today's date + input if it looks like time?
                # But we handled that above.
                return iso_str # Fallback

        start_str = normalize_iso(event_data['start'])
        end_str = normalize_iso(event_data['end'])
        
        # Safety fallback: If End is missing, assume +30 mins
        if not end_str and start_str:
            try:
                dt_start = datetime.datetime.fromisoformat(start_str)
                dt_end = dt_start + datetime.timedelta(minutes=30)
                end_str = dt_end.isoformat(timespec='seconds')
            except:
                pass

        # Construct body
        body = {
            'summary': event_data['name'],
            'description': event_data.get('description', 'Created by Daily Manager AI'),
            'start': {
                'dateTime': start_str,
                'timeZone': 'Europe/Berlin', 
            },
            'end': {
                'dateTime': end_str,
                'timeZone': 'Europe/Berlin',
            },
        }
        
        try:
            service.events().insert(calendarId='primary', body=body).execute()
            return True
        except Exception as api_err:
             logger.error(f"Google API Error Body: {body}")
             raise api_err
        
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return False
    finally:
        session.close()
