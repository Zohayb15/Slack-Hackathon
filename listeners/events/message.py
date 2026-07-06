from logging import Logger

from slack_bolt.context.async_context import AsyncBoltContext
from slack_bolt.context.say.async_say import AsyncSay
from slack_bolt.context.say_stream.async_say_stream import AsyncSayStream
from slack_bolt.context.set_status.async_set_status import AsyncSetStatus
from slack_sdk.web.async_client import AsyncWebClient

from agent import AgentDeps, run_agent
from services.extraction import extract_event_details
from thread_context import session_store
from listeners.views.event_confirm_builder import build_event_confirm_blocks
from listeners.views.feedback_builder import build_feedback_blocks

# Minimum extraction confidence before we post a confirmation prompt.
SCHEDULING_CONFIDENCE_THRESHOLD = 0.6


async def handle_message(
    client: AsyncWebClient,
    context: AsyncBoltContext,
    event: dict,
    logger: Logger,
    say: AsyncSay,
    say_stream: AsyncSayStream,
    set_status: AsyncSetStatus,
):
    """Handle messages sent to the agent via DM or in threads the bot is part of."""
    # Skip message subtypes (edits, deletes, etc.) and bot messages.
    if event.get("subtype"):
        return
    if event.get("bot_id"):
        return

    is_dm = event.get("channel_type") == "im"
    is_thread_reply = event.get("thread_ts") is not None

    if is_dm:
        pass
    elif is_thread_reply:
        # Channel thread replies are handled only if the bot is already engaged
        session = session_store.get_session(context.channel_id, event["thread_ts"])
        if session is None:
            return
    else:
        # Top-level channel messages: passively scan for scheduling intent.
        # (@mentions are handled separately by app_mentioned.)
        await detect_and_propose_event(client, context, event, logger)
        return

    try:
        channel_id = context.channel_id
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event["ts"]

        # Get session ID for conversation context
        existing_session_id = session_store.get_session(channel_id, thread_ts)

        # Set assistant thread status with loading messages
        await set_status(
            status="Thinking...",
            loading_messages=[
                "Teaching the hamsters to type faster…",
                "Untangling the internet cables…",
                "Consulting the office goldfish…",
                "Polishing up the response just for you…",
                "Convincing the AI to stop overthinking…",
            ],
        )

        # Run the agent with deps for tool access
        user_id = context.user_id
        deps = AgentDeps(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            message_ts=event["ts"],
            user_token=context.user_token,
        )
        response_text, new_session_id = await run_agent(
            text, session_id=existing_session_id, deps=deps
        )

        # Stream response in thread with feedback buttons
        streamer = await say_stream()
        await streamer.append(markdown_text=response_text)
        feedback_blocks = build_feedback_blocks()
        await streamer.stop(blocks=feedback_blocks)

        # Store session ID for future context
        if new_session_id:
            session_store.set_session(channel_id, thread_ts, new_session_id)

    except Exception as e:
        logger.exception(f"Failed to handle message: {e}")
        await say(
            text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event.get("ts"),
        )


async def detect_and_propose_event(
    client: AsyncWebClient,
    context: AsyncBoltContext,
    event: dict,
    logger: Logger,
):
    """Scan a top-level channel message for scheduling intent.

    If a concrete plan is detected with enough confidence, post a
    confirmation prompt (with Add/Ignore buttons) in the message's thread.
    Silently does nothing otherwise, so normal chatter is unaffected.
    """
    text = event.get("text", "")
    if not text or len(text) < 8:
        return

    try:
        details = await extract_event_details(text)
    except Exception as e:
        logger.warning(f"Scheduling extraction failed: {e}")
        return

    if not details.get("is_scheduling_intent"):
        return
    if details.get("confidence", 0) < SCHEDULING_CONFIDENCE_THRESHOLD:
        return
    if not details.get("date") or not details.get("start_time"):
        # Not concrete enough to schedule; skip rather than nag.
        return

    await client.chat_postMessage(
        channel=context.channel_id,
        thread_ts=event["ts"],
        text="Looks like you're scheduling something — confirm to add it to your calendar.",
        blocks=build_event_confirm_blocks(details),
    )
