"""Re-ingest Slack channel threads into Cognee /learn to rebuild the knowledge graph after data loss."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

COGNEE_URL = "http://localhost:8000"
SLACK_API = "https://slack.com/api"
DEFAULT_CHANNEL = "C0B2E1CHZ8T"
DEFAULT_OLDEST = "2026-05-08"
DEFAULT_LATEST = "2026-05-12"

# State file lives alongside this script so it's easy to find and reset
STATE_FILE = Path(__file__).parent / ".replay_state.json"


def load_env(path: str) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file; ignore blank lines and comments."""
    env: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def load_state() -> set[str]:
    """Return the set of thread_ts values already successfully ingested."""
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        return set(data.get("completed_thread_ts", []))
    return set()


def save_state(completed: set[str]) -> None:
    """Flush state to disk after every successful thread so re-runs are safe."""
    STATE_FILE.write_text(json.dumps({"completed_thread_ts": sorted(completed)}, indent=2))


def date_to_unix(date_str: str, end_of_day: bool = False) -> float:
    """Convert YYYY-MM-DD to a UTC Unix timestamp (start or end of day)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        # Use start of the *next* day as the exclusive upper bound
        from datetime import timedelta
        dt = dt + timedelta(days=1)
    return dt.timestamp()


def fetch_thread_roots(client: httpx.Client, token: str, channel: str, oldest: float, latest: float) -> list[dict[str, Any]]:
    """Return all root messages (thread_ts == ts) in the date range."""
    roots: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {
            "channel": channel,
            "oldest": str(oldest),
            "latest": str(latest),
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor

        resp = client.get(
            f"{SLACK_API}/conversations.history",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

        for msg in data.get("messages", []):
            ts = msg.get("ts", "")
            thread_ts = msg.get("thread_ts", ts)
            # A message is a thread root when thread_ts equals its own ts,
            # OR when it has no thread_ts (standalone message with no replies).
            # We include both so standalone messages also get ingested.
            if thread_ts == ts:
                roots.append(msg)

        meta = data.get("response_metadata", {})
        cursor = meta.get("next_cursor") or None
        if not cursor:
            break

    return roots


def fetch_replies(client: httpx.Client, token: str, channel: str, thread_ts: str) -> list[dict[str, Any]]:
    """Return all messages in a thread (first message is the root)."""
    resp = client.get(
        f"{SLACK_API}/conversations.replies",
        params={"channel": channel, "ts": thread_ts},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        raise RuntimeError(f"Slack replies API error: {data.get('error', 'unknown')}")

    return data.get("messages", [])


def format_thread(channel: str, messages: list[dict[str, Any]]) -> str:
    """
    Build the text blob to send to /learn.
    User IDs are included as-is (e.g. U0ABC123); no extra API calls for display names.
    """
    root = messages[0]
    ts_float = float(root.get("ts", "0"))
    date_str = datetime.fromtimestamp(ts_float, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    root_text = root.get("text", "").strip()

    lines = [f"Slack thread in #{channel} on {date_str}:", root_text]

    replies = messages[1:]  # everything after the root
    if replies:
        lines.append("\nReplies:")
        for msg in replies:
            user = msg.get("user", msg.get("bot_id", "unknown"))
            text = msg.get("text", "").strip()
            lines.append(f"- {user}: {text}")

    return "\n".join(lines)


def post_to_cognee(client: httpx.Client, text: str) -> dict[str, Any]:
    """POST a single thread to Cognee /learn and return the response body."""
    resp = client.post(
        f"{COGNEE_URL}/learn",
        json={"text": text},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay Slack threads into Cognee /learn.")
    parser.add_argument("--oldest", default=DEFAULT_OLDEST, help="Start date YYYY-MM-DD (inclusive, UTC)")
    parser.add_argument("--latest", default=DEFAULT_LATEST, help="End date YYYY-MM-DD (exclusive, UTC)")
    parser.add_argument("--channel", default=DEFAULT_CHANNEL, help="Slack channel ID")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count threads; skip POST to Cognee")
    parser.add_argument("--reset-state", action="store_true", help="Clear completed-thread state before starting")
    args = parser.parse_args()

    # Load Slack token from ~/.hermes/.env
    env_path = os.path.expanduser("~/.hermes/.env")
    env = load_env(env_path)
    token = env.get("SLACK_BOT_TOKEN", "")
    if not token:
        print("[fail] SLACK_BOT_TOKEN not found in ~/.hermes/.env", file=sys.stderr)
        return 1

    # Optionally wipe prior run state
    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()
        print("[info] State file cleared.")

    completed = load_state()

    oldest_ts = date_to_unix(args.oldest)
    # Use start of the day *after* --latest as the exclusive upper bound
    latest_ts = date_to_unix(args.latest, end_of_day=True)

    print(f"[info] Fetching threads from {args.oldest} to {args.latest} in channel {args.channel}")

    slack_client = httpx.Client(timeout=30.0)
    cognee_client = httpx.Client(timeout=30.0)

    try:
        roots = fetch_thread_roots(slack_client, token, args.channel, oldest_ts, latest_ts)
    except Exception as exc:
        print(f"[fail] Could not fetch channel history: {exc}", file=sys.stderr)
        return 1

    print(f"[info] Found {len(roots)} thread root(s)")

    if args.dry_run:
        skippable = sum(1 for r in roots if r.get("ts") in completed)
        print(f"[dry-run] Would process {len(roots) - skippable} thread(s) ({skippable} already completed).")
        return 0

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for root in roots:
        thread_ts = root.get("ts", "")

        if thread_ts in completed:
            print(f"[skip] thread {thread_ts}")
            skip_count += 1
            continue

        # Fetch full thread (root + replies)
        try:
            messages = fetch_replies(slack_client, token, args.channel, thread_ts)
        except Exception as exc:
            print(f"[fail] thread {thread_ts}: could not fetch replies — {exc}")
            fail_count += 1
            continue

        text = format_thread(args.channel, messages)

        try:
            post_to_cognee(cognee_client, text)
            completed.add(thread_ts)
            # Flush after every success so re-runs skip already-ingested threads
            save_state(completed)
            print(f"[ok] thread {thread_ts} ({len(text)} chars)")
            ok_count += 1
        except Exception as exc:
            print(f"[fail] thread {thread_ts}: POST to Cognee failed — {exc}")
            fail_count += 1

    print(f"\nProcessed {ok_count + skip_count + fail_count} threads "
          f"({ok_count} ok, {skip_count} skipped, {fail_count} failed)")

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
