import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import settings
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_events():
    """
    Fetches the upcoming 10 events for today.
    """
    creds = None
    # Token file stores the user's access and refresh tokens
    token_path = os.path.join(settings.BASE_DIR, 'token.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                return "Calendar Error: Token expired and refresh failed."
        else:
            # If no creds, we can't fetch. 
            # In a real app we'd trigger a flow, but for backend service we might need a stored token.
            return "Calendar: No credentials found. Please authenticate."

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        # End of day
        
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."
        
        event_summary = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_summary.append(f"- {event['summary']} at {start}")
            
        return "\n".join(event_summary)

    except Exception as e:
        logger.error(f"Calendar API Error: {e}")
        return f"Error fetching calendar: {str(e)}"
