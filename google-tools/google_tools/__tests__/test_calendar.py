"""Happy path / edge case / failure mode tests for calendar.py"""

from unittest.mock import MagicMock

import pytest

from google_tools.calendar import CalendarTools


def _make_calendar():
    """Create a CalendarTools with a fully mocked service, skipping Google API init."""
    cal = CalendarTools.__new__(CalendarTools)
    cal.service = MagicMock()
    return cal


class TestCalendarListEvents:
    def test_happy_returns_events(self):
        cal = _make_calendar()
        cal.service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "ev1",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-01-01T09:00:00"},
                    "end": {"dateTime": "2026-01-01T09:30:00"},
                    "attendees": [
                        {"email": "a@b.com", "responseStatus": "accepted"}
                    ],
                    "location": "Room 1",
                }
            ]
        }

        result = cal.list_events(max_results=5)
        assert len(result) == 1
        assert result[0]["summary"] == "Standup"
        assert result[0]["location"] == "Room 1"
        assert result[0]["attendees"][0]["email"] == "a@b.com"

    def test_edge_empty_calendar(self):
        cal = _make_calendar()
        cal.service.events().list().execute.return_value = {}

        result = cal.list_events()
        assert result == []

    def test_happy_with_time_filters(self):
        cal = _make_calendar()
        cal.service.events().list().execute.return_value = {"items": []}

        cal.list_events(
            time_min="2026-01-01T00:00:00Z",
            time_max="2026-01-02T00:00:00Z",
            max_results=20,
        )

        call_kwargs = cal.service.events().list.call_args[1]
        assert call_kwargs["timeMin"] == "2026-01-01T00:00:00Z"
        assert call_kwargs["timeMax"] == "2026-01-02T00:00:00Z"
        assert call_kwargs["maxResults"] == 20


class TestCalendarCreateEvent:
    def test_happy_creates_event(self):
        cal = _make_calendar()
        cal.service.events().insert().execute.return_value = {
            "id": "new-ev",
            "htmlLink": "https://calendar.google.com/new-ev",
        }

        result = cal.create_event(
            "Lunch", "2026-01-01T12:00:00", "2026-01-01T13:00:00",
            "Cafe", "Team lunch"
        )
        assert result["id"] == "new-ev"
        assert result["html_link"]

    def test_happy_minimal_fields(self):
        cal = _make_calendar()
        cal.service.events().insert().execute.return_value = {
            "id": "min-ev",
            "htmlLink": "https://calendar.google.com/min-ev",
        }

        result = cal.create_event("Quick", "2026-01-01T10:00:00", "2026-01-01T10:30:00")
        assert result["id"] == "min-ev"

    def test_failure_api_error(self):
        cal = _make_calendar()
        cal.service.events().insert.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            cal.create_event("X", "s", "e")


class TestCalendarUpdateEvent:
    def test_happy_updates_event(self):
        cal = _make_calendar()
        cal.service.events().get().execute.return_value = {
            "id": "ev1",
            "summary": "Old Title",
            "start": {"dateTime": "old"},
            "end": {"dateTime": "old"},
        }
        cal.service.events().update().execute.return_value = {
            "id": "ev1",
            "htmlLink": "https://calendar.google.com/ev1",
        }

        result = cal.update_event("ev1", summary="New Title", start="2026-01-01T09:00:00")
        assert result["id"] == "ev1"
        assert result["html_link"]

    def test_happy_partial_update(self):
        cal = _make_calendar()
        cal.service.events().get().execute.return_value = {
            "id": "ev2", "summary": "Keep",
        }
        cal.service.events().update().execute.return_value = {
            "id": "ev2", "htmlLink": "link",
        }

        result = cal.update_event("ev2", summary="Only title changed")
        assert result["id"] == "ev2"


class TestCalendarDeleteEvent:
    def test_happy_deletes_event(self):
        cal = _make_calendar()
        cal.service.events().delete().execute.return_value = {}

        result = cal.delete_event("ev-to-delete")
        assert result == {"deleted": True}

    def test_failure_event_not_found(self):
        cal = _make_calendar()
        cal.service.events().delete.side_effect = Exception("Not found")

        with pytest.raises(Exception, match="Not found"):
            cal.delete_event("nonexistent")
