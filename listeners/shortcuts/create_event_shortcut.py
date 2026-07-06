"""Message shortcut: explicitly create a calendar event from any message.

This is the manual entry point — the user picks "Add to calendar" from a
message's ... (more actions) menu. Unlike the passive channel scan, the user
explicitly asked, so we skip the confidence threshold; we still require a
concrete date and time before proposing anything.
"""

from logging import Logger

from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.event_confirm_builder import build_event_confirm_blocks
from services.extraction import extract_event_details


async def handle_create_event_shortcut(
    ack, shortcut: dict, client: AsyncWebClient, logger: Logger
):
    """Extract event details from the chosen message and post confirm buttons."""
    # Slack requires an ack within 3 seconds; do it before the LLM call.
    await ack()

    channel_id = shortcut["channel"]["id"]
    user_id = shortcut["user"]["id"]
    message = shortcut.get("message", {})
    message_ts = message.get("ts")
    text = message.get("text", "")

    if not text:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=":warning: That message has no text I can read.",
        )
        return

    try:
        details = await extract_event_details(text)
    except Exception as e:
        logger.exception(f"Shortcut extraction failed: {e}")
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=":warning: Couldn't analyze that message — please try again.",
        )
        return

    # The user explicitly triggered this, so no confidence gate — but we
    # still need a concrete date and time to build an event.
    if not details.get("date") or not details.get("start_time"):
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=(
                "I couldn't find a concrete date and time in that message. "
                'It works best on messages like "let\'s sync Thursday at 2pm".'
            ),
        )
        return

    await client.chat_postMessage(
        channel=channel_id,
        thread_ts=message_ts,
        text="Confirm to add this event to the calendar.",
        blocks=build_event_confirm_blocks(details),
    )
