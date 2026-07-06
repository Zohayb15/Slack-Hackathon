"""Block Kit builder for the event confirmation message.

The full event details are serialized as JSON into the button `value`
(Slack allows up to 2000 chars), so the action handler can create the
event without any server-side pending-state store.
"""

import json


def build_event_confirm_blocks(details: dict) -> list[dict]:
    """Build confirmation blocks for a proposed calendar event.

    Args:
        details: Dict with title, date, start_time, duration_minutes,
            attendees, location keys (extraction schema).
    """
    title = details.get("title") or "(untitled)"
    date = details.get("date") or "?"
    start_time = details.get("start_time") or "?"
    duration = details.get("duration_minutes") or 30
    attendees = details.get("attendees") or []
    location = details.get("location")

    lines = [
        ":calendar: *Looks like you're scheduling something!*",
        f"*Title:* {title}",
        f"*When:* {date} at {start_time} ({duration} min)",
    ]
    if location:
        lines.append(f"*Where:* {location}")
    if attendees:
        lines.append(f"*With:* {', '.join(attendees)}")

    payload = json.dumps(
        {
            "title": details.get("title"),
            "date": details.get("date"),
            "start_time": details.get("start_time"),
            "duration_minutes": details.get("duration_minutes"),
            "attendees": attendees,
            "location": location,
        },
        separators=(",", ":"),
    )

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
        {
            "type": "actions",
            "block_id": "meetingmate_event_confirm",
            "elements": [
                {
                    "type": "button",
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Add to calendar"},
                    "action_id": "calendar_confirm_yes",
                    "value": payload,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Ignore"},
                    "action_id": "calendar_confirm_no",
                    "value": "ignore",
                },
            ],
        },
    ]
