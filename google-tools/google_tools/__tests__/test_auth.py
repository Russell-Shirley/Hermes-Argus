"""Happy path / edge case / failure mode tests for auth.py"""

import os
import json
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from google_tools.auth import get_credentials, run_oauth_flow, TokenMissingError, SCOPES


class FakeCreds:
    def __init__(self, valid=True, expired=False, refresh_token="refresh-token-123"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.token = "access-token-abc"

    def to_json(self):
        return json.dumps({"token": self.token, "refresh_token": self.refresh_token})

    @staticmethod
    def from_authorized_user_file(path, scopes):
        with open(path) as f:
            data = json.load(f)
        return FakeCreds(refresh_token=data.get("refresh_token", ""))

    def refresh(self, request):
        self.valid = True
        self.expired = False


class TestGetCredentials:
    def test_happy_valid_token(self, monkeypatch):
        """Happy path: token.json exists with a valid token."""
        with tempfile.TemporaryDirectory() as tmp:
            token_path = os.path.join(tmp, "token.json")
            with open(token_path, "w") as f:
                json.dump({"token": "abc", "refresh_token": "ref-1"}, f)

            monkeypatch.setattr("google_tools.auth.TOKEN_PATH", token_path)

            with patch("google_tools.auth.Credentials", FakeCreds):
                creds = get_credentials()
                assert creds.valid is True

    def test_happy_expired_token_with_refresh(self, monkeypatch):
        """Happy path: token expired but has a refresh token -> refreshes."""
        with tempfile.TemporaryDirectory() as tmp:
            token_path = os.path.join(tmp, "token.json")
            with open(token_path, "w") as f:
                json.dump({"token": "old", "refresh_token": "ref-1"}, f)

            monkeypatch.setattr("google_tools.auth.TOKEN_PATH", token_path)

            with patch("google_tools.auth.Credentials") as MockCreds:
                fake = FakeCreds(valid=False, expired=True)
                MockCreds.from_authorized_user_file.return_value = fake
                creds = get_credentials()
                assert creds.valid is True

    def test_edge_missing_token_raises(self, monkeypatch):
        """Edge case: token.json missing -> TokenMissingError."""
        monkeypatch.setattr("google_tools.auth.TOKEN_PATH", "/nonexistent/token.json")
        monkeypatch.setattr("google_tools.auth.os.path.exists", lambda p: False)

        with pytest.raises(TokenMissingError, match="token is missing"):
            get_credentials()

    def test_failure_expired_and_no_refresh(self, monkeypatch):
        """Failure mode: token expired and no refresh token -> TokenMissingError."""
        with tempfile.TemporaryDirectory() as tmp:
            token_path = os.path.join(tmp, "token.json")
            with open(token_path, "w") as f:
                json.dump({"token": "old"}, f)

            monkeypatch.setattr("google_tools.auth.TOKEN_PATH", token_path)

            with patch("google_tools.auth.Credentials") as MockCreds:
                fake = FakeCreds(valid=False, expired=True, refresh_token=None)
                MockCreds.from_authorized_user_file.return_value = fake
                with pytest.raises(TokenMissingError, match="token is missing"):
                    get_credentials()


class TestRunOAuthFlow:
    def test_happy_flow_saves_token(self, monkeypatch):
        """Happy path: credentials.json present, OAuth flow completes, token saved."""
        with tempfile.TemporaryDirectory() as tmp:
            cred_path = os.path.join(tmp, "credentials.json")
            token_path = os.path.join(tmp, "token.json")
            with open(cred_path, "w") as f:
                json.dump({"installed": {}}, f)

            monkeypatch.setattr("google_tools.auth.CREDENTIALS_PATH", cred_path)
            monkeypatch.setattr("google_tools.auth.TOKEN_PATH", token_path)

            fake_flow = MagicMock()
            fake_creds = FakeCreds()

            with patch(
                "google_tools.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=fake_flow,
            ):
                fake_flow.run_local_server.return_value = fake_creds
                result = run_oauth_flow()
                assert os.path.exists(token_path)
                assert result.valid is True

    def test_failure_missing_credentials(self, monkeypatch):
        """Failure mode: credentials.json not found -> FileNotFoundError."""
        monkeypatch.setattr(
            "google_tools.auth.CREDENTIALS_PATH", "/nonexistent/creds.json"
        )
        with pytest.raises(FileNotFoundError, match="credentials.json not found"):
            run_oauth_flow()
