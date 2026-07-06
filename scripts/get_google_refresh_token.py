"""One-time helper: obtain a Google Calendar OAuth refresh token.

Prereqs (Google Cloud Console, console.cloud.google.com):
  1. Create/select a project
  2. Enable the "Google Calendar API"
  3. Configure the OAuth consent screen (External, add yourself as a test user)
  4. Create OAuth credentials -> "Desktop app" type
  5. Put the client ID/secret in .env as GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET

Then run from the repo root:
    python3 scripts/get_google_refresh_token.py

A browser window opens; sign in and grant access. The refresh token is
printed — copy it into .env as GOOGLE_REFRESH_TOKEN.
"""

import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def main():
    load_dotenv(dotenv_path=".env")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise SystemExit(
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first "
            "(see the docstring at the top of this script)."
        )

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    # access_type=offline + prompt=consent are required to get a refresh token.
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )

    print("\n" + "=" * 60)
    print("Add this line to your .env:")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
