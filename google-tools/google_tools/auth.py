import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")


class TokenMissingError(RuntimeError):
    pass


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise TokenMissingError(
                "Google token is missing or expired. "
                "Please run 'uv run oauth_setup.py' in the google-tools directory on the host machine."
            )
        _save_token(creds)

    return creds


def run_oauth_flow():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_PATH}. "
            "Download it from Google Cloud Console (APIs & Services > Credentials)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def _save_token(creds):
    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
