"""Action handlers for the event confirmation buttons."""

import asyncio
import json
from logging import Logger

from slack_sdk.web.async_client import AsyncWebClient

from services.google_calendar import create_event


async def handle_calendar_confirm_yes(
    ack, body: dict, client: AsyncWebClient, logger: Logger
):
    """User confirmed — create the Google Calendar event and update the message."""
    await ack()

    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    details = json.loads(body["actions"][0]["value"])

    try:
        # googleapiclient is sync; run it off the event loop.
        result = await asyncio.to_thread(
            create_event,
            title=details.get("title"),
            date=details.get("date"),
            start_time=details.get("start_time"),
            duration_minutes=details.get("duration_minutes"),
            attendees=details.get("attendees"),
            location=details.get("location"),
        )
        await client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Event created!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":white_check_mark: Added *{details.get('title') or 'Meeting'}* "
                            f"to your calendar — <{result['html_link']}|view event>"
                        ),
                    },
                }
            ],
        )
    except Exception as e:
        logger.exception(f"Failed to create calendar event: {e}")
        await client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Failed to create event.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            ":warning: Couldn't create the event — check that the "
                            "Google Calendar credentials in `.env` are set up. "
                            f"(`{type(e).__name__}`)"
                        ),
                    },
                }
            ],
        )


async def handle_calendar_confirm_no(
    ack, body: dict, client: AsyncWebClient, logger: Logger
):
    """User declined — replace the confirmation with a dismissal note."""
    await ack()
    await client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Okay, ignored.",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Okay, ignored :+1:"},
            }
        ],
    )
