"""Google Calendar integration.

Creates events on the primary calendar using an OAuth refresh token.
The googleapiclient library is synchronous, so async callers should wrap
create_event with asyncio.to_thread().
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri=GOOGLE_TOKEN_URI,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create_event(
    title: str,
    date: str,
    start_time: str,
    duration_minutes: int | None = 30,
    attendees: list[str] | None = None,
    location: str | None = None,
    timezone: str | None = None,
) -> dict:
    """Create a Google Calendar event and return {"event_id", "html_link"}.

    Args:
        title: Event title.
        date: ISO date, e.g. "2026-07-10".
        start_time: 24h "HH:MM".
        duration_minutes: Length of the event (default 30).
        attendees: List of attendee email addresses.
        location: Optional location string.
        timezone: IANA timezone; falls back to DEFAULT_TIMEZONE env var.
    """
    tz_name = timezone or os.environ.get("DEFAULT_TIMEZONE", "America/New_York")
    tz = ZoneInfo(tz_name)

    start_dt = datetime.fromisoformat(f"{date}T{start_time}").replace(tzinfo=tz)
    end_dt = start_dt + timedelta(minutes=duration_minutes or 30)

    event_body = {
        "summary": title or "Meeting",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": tz_name},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": tz_name},
    }
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    service = _get_service()
    created = (
        service.events()
        .insert(calendarId="primary", body=event_body, sendUpdates="all")
        .execute()
    )
    return {"event_id": created["id"], "html_link": created.get("htmlLink", "")}
