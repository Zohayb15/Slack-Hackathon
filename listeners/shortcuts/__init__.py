from slack_bolt.async_app import AsyncApp

from .create_event_shortcut import handle_create_event_shortcut


def register(app: AsyncApp):
    app.shortcut("meetingmate_create_event")(handle_create_event_shortcut)
