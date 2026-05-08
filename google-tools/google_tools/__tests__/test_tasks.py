"""Happy path / edge case / failure mode tests for tasks.py"""

from unittest.mock import MagicMock

import pytest

from google_tools.tasks import TasksTools


def _make_tasks():
    """Create a TasksTools with a fully mocked service, skipping Google API init."""
    tasks = TasksTools.__new__(TasksTools)
    tasks.service = MagicMock()
    return tasks


class TestTasksListLists:
    def test_happy_returns_lists(self):
        tasks = _make_tasks()
        tasks.service.tasklists().list().execute.return_value = {
            "items": [
                {"id": "l1", "title": "Personal"},
                {"id": "l2", "title": "Work"},
            ]
        }

        result = tasks.list_lists()
        assert len(result) == 2
        assert result[0] == {"id": "l1", "title": "Personal"}
        assert result[1]["id"] == "l2"

    def test_edge_no_lists(self):
        tasks = _make_tasks()
        tasks.service.tasklists().list().execute.return_value = {}

        result = tasks.list_lists()
        assert result == []


class TestTasksListTasks:
    def test_happy_returns_tasks(self):
        tasks = _make_tasks()
        tasks.service.tasks().list().execute.return_value = {
            "items": [
                {
                    "id": "t1",
                    "title": "Buy milk",
                    "notes": "2%",
                    "due": "2026-01-15T00:00:00Z",
                    "status": "needsAction",
                }
            ]
        }

        result = tasks.list_tasks("l1")
        assert len(result) == 1
        assert result[0]["title"] == "Buy milk"
        assert result[0]["status"] == "needsAction"

    def test_edge_no_tasks(self):
        tasks = _make_tasks()
        tasks.service.tasks().list().execute.return_value = {}

        result = tasks.list_tasks("empty-list")
        assert result == []

    def test_happy_hides_completed_by_default(self):
        tasks = _make_tasks()
        tasks.service.tasks().list().execute.return_value = {}

        tasks.list_tasks("l1")
        call_kwargs = tasks.service.tasks().list.call_args[1]
        assert call_kwargs.get("showCompleted") is False

    def test_happy_shows_completed_when_requested(self):
        tasks = _make_tasks()
        tasks.service.tasks().list().execute.return_value = {"items": []}

        tasks.list_tasks("l1", show_completed=True)
        call_kwargs = tasks.service.tasks().list.call_args[1]
        assert "showCompleted" not in call_kwargs


class TestTasksCreateTask:
    def test_happy_creates_task(self):
        tasks = _make_tasks()
        tasks.service.tasks().insert().execute.return_value = {
            "id": "new-task",
            "title": "New todo",
        }

        result = tasks.create_task("l1", "New todo", "Some notes", "2026-02-01T00:00:00Z")
        assert result["id"] == "new-task"
        assert result["title"] == "New todo"

        body = tasks.service.tasks().insert.call_args[1]["body"]
        assert body["title"] == "New todo"
        assert body["notes"] == "Some notes"
        assert body["due"] == "2026-02-01T00:00:00Z"

    def test_happy_minimal_create(self):
        tasks = _make_tasks()
        tasks.service.tasks().insert().execute.return_value = {
            "id": "t-min", "title": "Minimal",
        }

        result = tasks.create_task("l1", "Minimal")
        assert result["id"] == "t-min"
        body = tasks.service.tasks().insert.call_args[1]["body"]
        assert body == {"title": "Minimal"}

    def test_failure_api_error(self):
        tasks = _make_tasks()
        tasks.service.tasks().insert.side_effect = Exception("Quota exceeded")

        with pytest.raises(Exception, match="Quota exceeded"):
            tasks.create_task("l1", "Bad")


class TestTasksUpdateTask:
    def test_happy_updates_status(self):
        tasks = _make_tasks()
        tasks.service.tasks().get().execute.return_value = {
            "id": "t1",
            "title": "Old task",
            "status": "needsAction",
        }
        tasks.service.tasks().update().execute.return_value = {
            "id": "t1",
            "title": "Old task",
            "status": "completed",
        }

        result = tasks.update_task("l1", "t1", status="completed")
        assert result["status"] == "completed"

    def test_happy_no_status_change(self):
        tasks = _make_tasks()
        tasks.service.tasks().get().execute.return_value = {
            "id": "t2",
            "title": "Same",
            "status": "needsAction",
        }
        tasks.service.tasks().update().execute.return_value = {
            "id": "t2",
            "title": "Same",
            "status": "needsAction",
        }

        result = tasks.update_task("l1", "t2")
        assert result["status"] == "needsAction"

    def test_failure_task_not_found(self):
        tasks = _make_tasks()
        tasks.service.tasks().get.side_effect = Exception("Not found")

        with pytest.raises(Exception, match="Not found"):
            tasks.update_task("l1", "ghost")
