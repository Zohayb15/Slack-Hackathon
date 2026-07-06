from calendar_tool import create_event

link = create_event(
    summary="MeetingMate Test Event",
    start_iso="2026-07-08T14:00:00",
    end_iso="2026-07-08T15:00:00",
)
print("Created:", link)