"""Scheduling intent detection and event detail extraction.

Uses a direct (lightweight) Anthropic API call rather than the full Agent SDK,
so it's cheap enough to run passively on every channel message.
"""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from anthropic import AsyncAnthropic

_client: AsyncAnthropic | None = None

EXTRACTION_SYSTEM_PROMPT = """\
You detect whether a Slack message expresses intent to schedule a meeting or event.
If it does, extract structured details. Respond ONLY with raw JSON — no prose, no markdown fences.

Schema:
{
  "is_scheduling_intent": boolean,
  "title": string | null,
  "date": string | null,        // ISO 8601 date, e.g. "2026-07-10"
  "start_time": string | null,  // 24h HH:MM, e.g. "14:00"
  "duration_minutes": number | null,
  "attendees": string[] | null, // email addresses only; omit names without emails
  "location": string | null,
  "confidence": number          // 0-1
}

Rules:
- Resolve relative dates ("tomorrow", "next Tuesday") using the provided current_datetime.
- Only mark is_scheduling_intent true for concrete plans (a proposed time/day),
  not vague ones ("we should catch up sometime").
- If is_scheduling_intent is false, all other fields must be null.
- Default duration_minutes to 30 if a time is given but no duration.
- Generate a short, sensible title from context if none is stated (e.g. "Team sync").
"""


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def extract_event_details(message_text: str) -> dict:
    """Detect scheduling intent in a message and extract structured event details.

    Returns a dict matching the schema in EXTRACTION_SYSTEM_PROMPT. On any
    parse failure, returns a safe "no intent" result.
    """
    tz = ZoneInfo(os.environ.get("DEFAULT_TIMEZONE", "America/New_York"))
    now = datetime.now(tz).isoformat()

    response = await _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f'current_datetime: {now}\nmessage: """{message_text}"""',
            }
        ],
    )

    raw = "".join(block.text for block in response.content if block.type == "text")
    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            raise ValueError("not a dict")
        result.setdefault("is_scheduling_intent", False)
        result.setdefault("confidence", 0)
        return result
    except (json.JSONDecodeError, ValueError):
        return {"is_scheduling_intent": False, "confidence": 0}
