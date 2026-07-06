"""Agent tool: propose a calendar event with confirmation buttons."""

from claude_agent_sdk import tool

from agent.context import agent_deps_var
from listeners.views.event_confirm_builder import build_event_confirm_blocks

PROPOSE_DESCRIPTION = """\
Propose a calendar event to the user with Add/Ignore confirmation buttons in Slack.

Use this whenever the user asks to schedule a meeting or event, or clearly \
expresses concrete scheduling intent (a specific day and time). Do NOT create \
the event yourself or claim it was created — this tool only posts a proposal; \
the user confirms via the buttons. After calling it, briefly tell the user to \
confirm using the buttons above.

Resolve relative dates ("tomorrow", "next Tuesday") to concrete ISO dates \
before calling. If the user gave no duration, use 30 minutes.
"""


@tool(
    name="propose_calendar_event",
    description=PROPOSE_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short event title."},
            "date": {"type": "string", "description": "ISO date, e.g. 2026-07-10."},
            "start_time": {"type": "string", "description": "24h HH:MM, e.g. 14:00."},
            "duration_minutes": {"type": "number", "description": "Default 30."},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Attendee email addresses (emails only).",
            },
            "location": {"type": "string"},
        },
        "required": ["title", "date", "start_time"],
    },
)
async def propose_calendar_event_tool(args):
    """Post the confirmation blocks into the current thread."""
    deps = agent_deps_var.get()

    details = {
        "title": args.get("title"),
        "date": args.get("date"),
        "start_time": args.get("start_time"),
        "duration_minutes": args.get("duration_minutes") or 30,
        "attendees": args.get("attendees") or [],
        "location": args.get("location"),
    }

    await deps.client.chat_postMessage(
        channel=deps.channel_id,
        thread_ts=deps.thread_ts,
        text="Confirm to add this event to your calendar.",
        blocks=build_event_confirm_blocks(details),
    )
    return {
        "content": [
            {
                "type": "text",
                "text": "Proposal posted with confirmation buttons. The event is NOT created yet — the user must confirm.",
            }
        ]
    }
