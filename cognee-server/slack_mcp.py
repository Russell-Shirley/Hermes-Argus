"""Slack reactions MCP server.

Exposes add/remove reaction tools so Argus can signal task status without
needing direct access to SLACK_BOT_TOKEN (inherited from Hermes's env).
"""

import os
import json
import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("slack")

SLACK_API = "https://slack.com/api"


def _call(endpoint: str, payload: dict) -> dict:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return {"ok": False, "error": "missing_token"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{SLACK_API}/{endpoint}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def slack_add_reaction(channel: str, timestamp: str, name: str) -> str:
    """Add an emoji reaction to a Slack message."""
    result = _call("reactions.add", {"channel": channel, "timestamp": timestamp, "name": name})
    return json.dumps(result)


@mcp.tool()
def slack_remove_reaction(channel: str, timestamp: str, name: str) -> str:
    """Remove an emoji reaction from a Slack message."""
    result = _call("reactions.remove", {"channel": channel, "timestamp": timestamp, "name": name})
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
