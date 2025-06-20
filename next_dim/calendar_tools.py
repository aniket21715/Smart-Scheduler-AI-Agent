import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes define the level of access you are requesting from the user.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Initializes and returns a Google Calendar API service object."""
    creds = None
    
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Opening browser for authentication...")
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("credentials.json not found. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            print("Please complete the authentication in your browser...")
            creds = flow.run_local_server(port=0)
            print("Authentication successful!")
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            print("Credentials saved for future use.")
            
    service = build("calendar", "v3", credentials=creds)
    
    # Test the connection
    try:
        calendar_list = service.calendarList().list().execute()
        print(f"Successfully connected to calendar. Found {len(calendar_list.get('items', []))} calendars.")
    except HttpError as error:
        print(f"An error occurred testing calendar connection: {error}")
        raise
        
    return service

def find_available_slots(duration_minutes: int, date_str: str) -> str:
    """
    Finds available time slots on a given date for a specified duration.
    
    Args:
        duration_minutes: The desired duration of the meeting in minutes.
        date_str: The date to check for available slots, in 'YYYY-MM-DD' format.
    
    Returns:
        A JSON string with available time slots.
    """
    try:
        service = get_calendar_service()
        
        # Parse the date and set the time range (e.g., 9 AM to 5 PM)
        day = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        time_min = datetime.datetime.combine(day, datetime.time(9, 0))
        time_max = datetime.datetime.combine(day, datetime.time(17, 0))

        print(f"Checking availability on {date_str} from 9 AM to 5 PM for {duration_minutes} minutes...")

        # Get busy times from the calendar
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min.isoformat() + "Z",
            timeMax=time_max.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        print(f"Found {len(events)} existing events on this date.")

        # Extract busy time slots
        busy_slots = []
        for event in events:
            start_time = event["start"].get("dateTime")
            end_time = event["end"].get("dateTime")
            
            if start_time and end_time:  # Only process events with specific times
                start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                # Convert to local time (remove timezone info for simplicity)
                start = start.replace(tzinfo=None)
                end = end.replace(tzinfo=None)
                busy_slots.append((start, end))
                print(f"Busy: {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}")

        # Find available slots
        available_slots = []
        slot_start = time_min
        
        while slot_start + datetime.timedelta(minutes=duration_minutes) <= time_max:
            slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
            is_free = True
            
            # Check for conflicts with existing events
            for busy_start, busy_end in busy_slots:
                # Check for overlap
                if max(slot_start, busy_start) < min(slot_end, busy_end):
                    is_free = False
                    break
            
            if is_free:
                available_slots.append({
                    "time": slot_start.strftime("%I:%M %p"),
                    "time_24h": slot_start.strftime("%H:%M"),
                    "datetime": slot_start.strftime("%Y-%m-%d %H:%M")
                })

            # Check in 30-minute increments
            slot_start += datetime.timedelta(minutes=30)

        if not available_slots:
            return json.dumps({
                "status": "no_slots", 
                "message": f"No available {duration_minutes}-minute slots found on {date_str} between 9 AM and 5 PM.",
                "suggestion": "Would you like to try a different date or time range?"
            })
            
        return json.dumps({
            "status": "success", 
            "date": date_str,
            "duration_minutes": duration_minutes,
            "available_slots": available_slots[:6]  # Limit to 6 options
        })

    except Exception as e:
        print(f"Error in find_available_slots: {e}")
        return json.dumps({"status": "error", "message": str(e)})

def schedule_meeting(title: str, duration_minutes: int, start_datetime: str, description: str = "") -> str:
    """
    Schedules a meeting in the user's Google Calendar.
    
    Args:
        title: The meeting title/subject
        duration_minutes: The length of the meeting in minutes
        start_datetime: The start time in 'YYYY-MM-DD HH:MM' format
        description: Optional meeting description
    
    Returns:
        A JSON string with the result of the scheduling attempt.
    """
    try:
        service = get_calendar_service()
        
        # Parse the start datetime
        start_dt = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        
        print(f"Scheduling meeting: '{title}' from {start_dt.strftime('%Y-%m-%d %I:%M %p')} to {end_dt.strftime('%I:%M %p')}")
        
        # Create the event
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC',  # You might want to use local timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC',
            },
        }

        # Insert the event
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        print(f"✓ Event created successfully! Event ID: {created_event.get('id')}")
        
        return json.dumps({
            "status": "success",
            "message": f"Meeting '{title}' scheduled successfully for {start_dt.strftime('%A, %B %d at %I:%M %p')}",
            "event_id": created_event.get('id'),
            "event_link": created_event.get('htmlLink', ''),
            "details": {
                "title": title,
                "start_time": start_dt.strftime('%Y-%m-%d %I:%M %p'),
                "end_time": end_dt.strftime('%Y-%m-%d %I:%M %p'),
                "duration": f"{duration_minutes} minutes"
            }
        })

    except HttpError as error:
        print(f"An error occurred: {error}")
        return json.dumps({
            "status": "error", 
            "message": f"Failed to schedule meeting: {error}"
        })
    except Exception as e:
        print(f"Error in schedule_meeting: {e}")
        return json.dumps({
            "status": "error", 
            "message": str(e)
        })

def get_upcoming_events(max_results: int = 10) -> str:
    """
    Gets upcoming events from the user's calendar.
    
    Args:
        max_results: Maximum number of events to return
    
    Returns:
        A JSON string with upcoming events.
    """
    try:
        service = get_calendar_service()
        
        # Get current time
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        upcoming_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            upcoming_events.append({
                'title': event.get('summary', 'No Title'),
                'start': start,
                'id': event.get('id')
            })
        
        return json.dumps({
            "status": "success",
            "events": upcoming_events
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })