"""Happy path / edge case / failure mode tests for gmail.py"""

import base64
from unittest.mock import MagicMock

import pytest

from google_tools.gmail import GmailTools


def _make_gmail():
    """Create a GmailTools with a fully mocked service, skipping Google API init."""
    gmail = GmailTools.__new__(GmailTools)
    gmail.service = MagicMock()
    return gmail


class TestGmailListMessages:
    def test_happy_returns_messages(self):
        gmail = _make_gmail()
        gmail.service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1", "threadId": "t1"}]
        }
        gmail.service.users().messages().get().execute.return_value = {
            "id": "1",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "a@b.com"},
                    {"name": "Date", "value": "Mon"},
                ]
            },
            "snippet": "Hi there",
        }

        result = gmail.list_messages(max_results=5)
        assert len(result) == 1
        assert result[0]["subject"] == "Hello"
        assert result[0]["from"] == "a@b.com"
        assert result[0]["id"] == "1"

    def test_edge_empty_inbox(self):
        gmail = _make_gmail()
        gmail.service.users().messages().list().execute.return_value = {}

        result = gmail.list_messages()
        assert result == []


class TestGmailSearch:
    def test_happy_returns_results(self):
        gmail = _make_gmail()
        gmail.service.users().messages().list().execute.return_value = {
            "messages": [{"id": "2", "threadId": "t2"}]
        }
        gmail.service.users().messages().get().execute.return_value = {
            "id": "2",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Invoice"},
                    {"name": "From", "value": "billing@co.com"},
                    {"name": "Date", "value": "Tue"},
                ]
            },
            "snippet": "Your invoice",
        }

        result = gmail.search("invoice", max_results=3)
        assert len(result) == 1
        assert result[0]["subject"] == "Invoice"

    def test_edge_no_results(self):
        gmail = _make_gmail()
        gmail.service.users().messages().list().execute.return_value = {}

        result = gmail.search("zzz_nonexistent")
        assert result == []


class TestGmailReadMessage:
    def test_happy_returns_full_message(self):
        gmail = _make_gmail()
        body_text = base64.urlsafe_b64encode(b"Hello World").decode()
        gmail.service.users().messages().get().execute.return_value = {
            "id": "3",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "From", "value": "me@here.com"},
                    {"name": "To", "value": "you@there.com"},
                    {"name": "Date", "value": "Wed"},
                ],
                "body": {"data": body_text},
            },
        }

        result = gmail.read_message("3")
        assert result["id"] == "3"
        assert result["subject"] == "Test"
        assert result["body_text"] == "Hello World"

    def test_handles_multipart_body(self):
        gmail = _make_gmail()
        body_data = base64.urlsafe_b64encode(b"Multipart body").decode()
        gmail.service.users().messages().get().execute.return_value = {
            "id": "4",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Multi"},
                    {"name": "From", "value": "f@b.com"},
                    {"name": "To", "value": "t@b.com"},
                    {"name": "Date", "value": "Thu"},
                ],
                "parts": [
                    {"mimeType": "text/html", "body": {}},
                    {"mimeType": "text/plain", "body": {"data": body_data}},
                ],
            },
        }

        result = gmail.read_message("4")
        assert result["body_text"] == "Multipart body"

    def test_edge_no_body(self):
        gmail = _make_gmail()
        gmail.service.users().messages().get().execute.return_value = {
            "id": "5",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Empty"},
                    {"name": "From", "value": "n@b.com"},
                    {"name": "To", "value": "x@b.com"},
                    {"name": "Date", "value": "Fri"},
                ],
            },
        }

        result = gmail.read_message("5")
        assert result["body_text"] == ""


class TestGmailSend:
    def test_happy_sends_and_returns_ids(self):
        gmail = _make_gmail()
        gmail.service.users().messages().send().execute.return_value = {
            "id": "msg-99",
            "threadId": "thread-99",
        }

        result = gmail.send("to@b.com", "Subject line", "Body text")
        assert result["message_id"] == "msg-99"
        assert result["thread_id"] == "thread-99"

    def test_failure_service_error(self):
        gmail = _make_gmail()
        gmail.service.users().messages().send.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            gmail.send("x@y.com", "S", "B")
