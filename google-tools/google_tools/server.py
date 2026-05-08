import json
import sys
import traceback

from mcp.server.fastmcp import FastMCP

from .auth import get_credentials, TokenMissingError
from .calendar import CalendarTools
from .gmail import GmailTools
from .tasks import TasksTools

mcp = FastMCP("google-workspace")


def _warn(msg):
    print(msg, file=sys.stderr, flush=True)


@mcp.tool()
def gmail__list_messages(max_results: int = 10) -> str:
    creds = get_credentials()
    gmail = GmailTools(creds)
    return json.dumps(gmail.list_messages(max_results))


@mcp.tool()
def gmail__search(query: str, max_results: int = 10) -> str:
    creds = get_credentials()
    gmail = GmailTools(creds)
    return json.dumps(gmail.search(query, max_results))


@mcp.tool()
def gmail__read_message(message_id: str) -> str:
    creds = get_credentials()
    gmail = GmailTools(creds)
    return json.dumps(gmail.read_message(message_id))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def gmail__send(to: str, subject: str, body: str) -> str:
    creds = get_credentials()
    gmail = GmailTools(creds)
    return json.dumps(gmail.send(to, subject, body))


@mcp.tool()
def calendar__list_events(
    time_min: str = None,
    time_max: str = None,
    max_results: int = 10,
) -> str:
    creds = get_credentials()
    cal = CalendarTools(creds)
    return json.dumps(cal.list_events(time_min, time_max, max_results))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def calendar__create_event(
    summary: str,
    start: str,
    end: str,
    location: str = "",
    description: str = "",
) -> str:
    creds = get_credentials()
    cal = CalendarTools(creds)
    return json.dumps(cal.create_event(summary, start, end, location, description))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def calendar__update_event(
    event_id: str,
    summary: str = None,
    start: str = None,
    end: str = None,
) -> str:
    creds = get_credentials()
    cal = CalendarTools(creds)
    return json.dumps(cal.update_event(event_id, summary, start, end))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def calendar__delete_event(event_id: str) -> str:
    creds = get_credentials()
    cal = CalendarTools(creds)
    return json.dumps(cal.delete_event(event_id))


@mcp.tool()
def tasks__list_lists() -> str:
    creds = get_credentials()
    tasks = TasksTools(creds)
    return json.dumps(tasks.list_lists())


@mcp.tool()
def tasks__list_tasks(list_id: str, show_completed: bool = False) -> str:
    creds = get_credentials()
    tasks = TasksTools(creds)
    return json.dumps(tasks.list_tasks(list_id, show_completed))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def tasks__create_task(
    list_id: str,
    title: str,
    notes: str = "",
    due: str = "",
) -> str:
    creds = get_credentials()
    tasks = TasksTools(creds)
    return json.dumps(tasks.create_task(list_id, title, notes, due))


@mcp.tool(annotations={"destructive": True, "readOnlyHint": False})
def tasks__update_task(
    list_id: str,
    task_id: str,
    status: str = None,
) -> str:
    creds = get_credentials()
    tasks = TasksTools(creds)
    return json.dumps(tasks.update_task(list_id, task_id, status))


def main():
    try:
        get_credentials()
    except TokenMissingError as e:
        _warn(f"⚠ google-workspace: {e}")
        _warn("⚠ google-workspace: Running in degraded mode (read-only tools unavailable).")
    except FileNotFoundError as e:
        _warn(f"⚠ google-workspace: {e}")
        _warn("⚠ google-workspace: Running in degraded mode (no credentials).")
    except Exception as e:
        _warn(f"⚠ google-workspace: Unexpected auth error: {e}")
        traceback.print_exc(file=sys.stderr)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
