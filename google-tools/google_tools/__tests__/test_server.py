"""Happy path / edge case / failure mode tests for server.py"""

import json
from unittest.mock import patch, MagicMock

import pytest

from google_tools.server import mcp


class TestServerToolRegistration:
    def test_all_12_tools_registered(self):
        """Happy path: all 12 tools are registered with correct names."""
        tool_names = {t.name for t in mcp._tool_manager._tools.values()}
        expected = {
            "gmail__list_messages",
            "gmail__search",
            "gmail__read_message",
            "gmail__send",
            "calendar__list_events",
            "calendar__create_event",
            "calendar__update_event",
            "calendar__delete_event",
            "tasks__list_lists",
            "tasks__list_tasks",
            "tasks__create_task",
            "tasks__update_task",
        }
        assert tool_names == expected

    @pytest.mark.parametrize("tool_name", [
        "gmail__send",
        "calendar__create_event",
        "calendar__update_event",
        "calendar__delete_event",
        "tasks__create_task",
        "tasks__update_task",
    ])
    def test_destructive_tools_marked_destructive(self, tool_name):
        """Destructive tools have annotations.destructive = True."""
        tool = mcp._tool_manager._tools[tool_name]
        assert tool.annotations is not None
        assert tool.annotations.destructive is True
        assert tool.annotations.readOnlyHint is False

    @pytest.mark.parametrize("tool_name", [
        "gmail__list_messages",
        "gmail__search",
        "gmail__read_message",
        "calendar__list_events",
        "tasks__list_lists",
        "tasks__list_tasks",
    ])
    def test_read_only_tools_not_marked_destructive(self, tool_name):
        """Read-only tools do NOT have destructive annotation."""
        tool = mcp._tool_manager._tools[tool_name]
        assert tool.annotations is None or tool.annotations.destructive is not True


class TestServerStderrOutput:
    def test_token_missing_warns_to_stderr(self):
        """When token is missing, warning goes to stderr."""
        with patch("google_tools.server.get_credentials") as mock_creds:
            from google_tools.auth import TokenMissingError
            mock_creds.side_effect = TokenMissingError("no token")
            
            from google_tools.server import main
            import sys
            import io
            
            captured = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured
            try:
                with patch.object(mcp, "run") as mock_run:
                    main()
                output = captured.getvalue()
                assert "google-workspace" in output
                assert "degraded" in output
            finally:
                sys.stderr = old_stderr
