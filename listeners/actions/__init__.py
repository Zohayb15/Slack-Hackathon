from slack_bolt.async_app import AsyncApp

from .calendar_confirm import handle_calendar_confirm_no, handle_calendar_confirm_yes
from .feedback_buttons import handle_feedback_button


def register(app: AsyncApp):
    app.action("feedback")(handle_feedback_button)
    app.action("calendar_confirm_yes")(handle_calendar_confirm_yes)
    app.action("calendar_confirm_no")(handle_calendar_confirm_no)
