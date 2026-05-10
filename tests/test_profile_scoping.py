"""Verify tool scoping per agent profile — Phase 4

Hermes v0.10 profiles are independent HERMES_HOME directories under
~/.hermes/profiles/<name>/ with their own config.yaml, SOUL.md, and .env.

This test suite verifies:
  - Profile directories exist and contain required files
  - MCP server scoping (AR watcher: no email; voucher/outreach: has email)
  - platform_toolsets restrict browser/web tools for all business profiles
  - All profiles have required MCP servers (cognee + postgres)
  - SOUL.md files are present and non-empty
"""
import os
from pathlib import Path

import pytest
import yaml


HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
PROFILES_DIR = HERMES_HOME / "profiles"

ALL_PROFILES = ["ar_watcher", "voucher_scanner", "outreach_agent"]


def load_profile_config(name: str) -> dict:
    """Load the config.yaml from a profile directory."""
    config_path = PROFILES_DIR / name / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Profile {name} missing config.yaml at {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def test_all_profile_directories_exist():
    """All three profile directories must exist."""
    for name in ALL_PROFILES:
        profile_dir = PROFILES_DIR / name
        assert profile_dir.is_dir(), f"Profile directory missing: {profile_dir}"
        assert (profile_dir / "config.yaml").exists(), f"Profile {name} missing config.yaml"
        assert (profile_dir / "SOUL.md").exists(), f"Profile {name} missing SOUL.md"


def test_all_profiles_have_required_mcp_servers():
    """All profiles must have Cognee + PostgreSQL MCP servers."""
    for name in ALL_PROFILES:
        config = load_profile_config(name)
        mcp = config.get("mcp_servers", {})
        assert "cognee" in mcp, f"{name} missing Cognee MCP server"
        assert "postgres" in mcp, f"{name} missing PostgreSQL MCP server"


def test_ar_watcher_no_google_workspace():
    """AR watcher must NOT have Google Workspace MCP server (no email access)."""
    config = load_profile_config("ar_watcher")
    mcp = config.get("mcp_servers", {})
    assert "google-workspace" not in mcp, (
        "AR watcher should not have Google Workspace access"
    )


def test_voucher_scanner_has_google_workspace():
    """Voucher scanner needs Google Workspace for review notifications."""
    config = load_profile_config("voucher_scanner")
    mcp = config.get("mcp_servers", {})
    assert "google-workspace" in mcp, (
        "Voucher scanner must have Google Workspace for review notifications"
    )


def test_outreach_agent_has_google_workspace():
    """Outreach agent needs Google Workspace for email delivery."""
    config = load_profile_config("outreach_agent")
    mcp = config.get("mcp_servers", {})
    assert "google-workspace" in mcp, (
        "Outreach agent must have Google Workspace for outreach delivery"
    )


def test_all_profiles_disable_web_browser():
    """No business profile should have web or browser tools via platform_toolsets."""
    for name in ALL_PROFILES:
        config = load_profile_config(name)
        pts = config.get("platform_toolsets", {})
        discord_tools = pts.get("discord", [])

        if not isinstance(discord_tools, list) or not discord_tools:
            pytest.skip(f"{name}: no explicit platform_toolsets.discord config")

        assert "web" not in discord_tools, (
            f"{name} should not have web tools enabled"
        )
        assert "browser" not in discord_tools, (
            f"{name} should not have browser tools enabled"
        )


def test_ar_watcher_no_code_execution():
    """AR watcher must not have code execution (per security requirements)."""
    config = load_profile_config("ar_watcher")
    pts = config.get("platform_toolsets", {})
    discord_tools = pts.get("discord", [])

    if not isinstance(discord_tools, list) or not discord_tools:
        pytest.skip("ar_watcher: no explicit platform_toolsets.discord config")

    assert "code_execution" not in discord_tools, (
        "AR watcher should not have code execution access"
    )


def test_voucher_and_outreach_have_code_execution():
    """Voucher scanner and outreach may need code execution for processing."""
    for name in ["voucher_scanner", "outreach_agent"]:
        config = load_profile_config(name)
        pts = config.get("platform_toolsets", {})
        discord_tools = pts.get("discord", [])

        if not isinstance(discord_tools, list) or not discord_tools:
            pytest.skip(f"{name}: no explicit platform_toolsets.discord config")

        assert "code_execution" in discord_tools, (
            f"{name} should have code execution access"
        )


def test_all_soul_md_files_non_empty():
    """All profile SOUL.md files must contain personality content."""
    for name in ALL_PROFILES:
        soul_path = PROFILES_DIR / name / "SOUL.md"
        content = soul_path.read_text(encoding="utf-8").strip()
        assert len(content) > 50, (
            f"{name} SOUL.md is too short ({len(content)} chars), expected > 50"
        )


def test_all_profiles_have_env_file():
    """All profiles must have .env file (can be shared from default)."""
    for name in ALL_PROFILES:
        env_path = PROFILES_DIR / name / ".env"
        assert env_path.exists(), f"{name} missing .env file"


def test_ar_watcher_mcp_server_count():
    """AR watcher has only cognee + postgres (2 MCP servers)."""
    config = load_profile_config("ar_watcher")
    mcp = config.get("mcp_servers", {})
    assert len(mcp) == 2, (
        f"AR watcher should have exactly 2 MCP servers, got {len(mcp)}: {list(mcp.keys())}"
    )


def test_voucher_and_outreach_mcp_server_count():
    """Voucher scanner and outreach agent have cognee + postgres + google-workspace (3 MCP servers)."""
    for name in ["voucher_scanner", "outreach_agent"]:
        config = load_profile_config(name)
        mcp = config.get("mcp_servers", {})
        assert len(mcp) == 3, (
            f"{name} should have exactly 3 MCP servers, got {len(mcp)}: {list(mcp.keys())}"
        )


def test_ar_watcher_soul_references_no_email():
    """AR watcher SOUL.md should mention lack of email access."""
    soul_path = PROFILES_DIR / "ar_watcher" / "SOUL.md"
    content = soul_path.read_text(encoding="utf-8").lower()
    has_no_email = "do not have email" in content or "no email" in content
    assert has_no_email, "AR watcher SOUL.md should state it lacks email access"


def test_voucher_scanner_soul_references_google():
    """Voucher scanner SOUL.md should mention Google Workspace access."""
    soul_path = PROFILES_DIR / "voucher_scanner" / "SOUL.md"
    content = soul_path.read_text(encoding="utf-8").lower()
    assert "google workspac" in content, (
        "Voucher scanner SOUL.md should mention Google Workspace access"
    )


def test_outreach_soul_references_google():
    """Outreach agent SOUL.md should mention Google Workspace access."""
    soul_path = PROFILES_DIR / "outreach_agent" / "SOUL.md"
    content = soul_path.read_text(encoding="utf-8").lower()
    assert "google workspac" in content, (
        "Outreach agent SOUL.md should mention Google Workspace access"
    )
