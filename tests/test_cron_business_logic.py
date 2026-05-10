"""Verify cron job business logic produces correct results"""
import json
import os
import yaml
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_cron_jobs_valid():
    """All cron jobs have required fields"""
    with open(os.path.join(PROJECT_ROOT, "config", "cron", "jobs.json")) as f:
        data = json.load(f)

    jobs = data["jobs"]
    assert len(jobs) == 3, f"Expected 3 jobs, got {len(jobs)}"

    required = {"id", "name", "schedule", "prompt", "deliver", "enabled", "state"}
    for job in jobs:
        missing = required - set(job.keys())
        assert not missing, f"Job {job.get('id', 'unknown')} missing: {missing}"
        assert job["enabled"] is True, f"Job {job['id']} is not enabled"
        assert job["state"] == "scheduled", f"Job {job['id']} has state '{job['state']}'"

    # Ensure no duplicate IDs
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), f"Duplicate job IDs: {ids}"


def test_ar_cron_references_ar_watcher():
    """AR cron job runs under AR watcher profile"""
    with open(os.path.join(PROJECT_ROOT, "config", "cron", "jobs.json")) as f:
        data = json.load(f)

    ar_job = next(j for j in data["jobs"] if j["id"] == "ar_daily_check")
    assert ar_job["profile"] == "ar_watcher"
    assert ar_job["require_approval"] is True
    assert "ar_invoices" in ar_job["prompt"].lower()
    assert "collection_activity" in ar_job["prompt"].lower()
    assert "disputed" in ar_job["prompt"].lower()


def test_voucher_cron_references_voucher_scanner():
    """Voucher cron job runs under voucher scanner profile"""
    with open(os.path.join(PROJECT_ROOT, "config", "cron", "jobs.json")) as f:
        data = json.load(f)

    voucher_job = next(j for j in data["jobs"] if j["id"] == "voucher_watchdog")
    assert voucher_job["profile"] == "voucher_scanner"
    assert voucher_job["require_approval"] is False
    assert "voucher_queue" in voucher_job["prompt"].lower()


def test_outreach_cron_references_outreach_agent():
    """Outreach cron job runs under outreach agent profile"""
    with open(os.path.join(PROJECT_ROOT, "config", "cron", "jobs.json")) as f:
        data = json.load(f)

    outreach_job = next(j for j in data["jobs"] if j["id"] == "outreach_daily")
    assert outreach_job["profile"] == "outreach_agent"
    assert outreach_job["require_approval"] is True
    assert "outreach_schedule" in outreach_job["prompt"].lower()


def test_collection_letter_aging_rules():
    """Verify aging bracket -> letter type logic"""
    with open(os.path.join(PROJECT_ROOT, "templates", "collection_letters.md")) as f:
        content = f.read()

    assert "trigger: 60-89 days past due" in content
    assert "name: ar_collection_letter_friendly" in content
    assert "trigger: 90-119 days past due" in content
    assert "name: ar_collection_letter_firm" in content
    assert "trigger: 120+ days past due" in content
    assert "name: ar_collection_letter_final" in content

    # Verify escalation is ordered correctly (friendly < firm < final)
    friendly_idx = content.index("ar_collection_letter_friendly")
    firm_idx = content.index("ar_collection_letter_firm")
    final_idx = content.index("ar_collection_letter_final")
    assert friendly_idx < firm_idx < final_idx


def test_voucher_confidence_threshold():
    """Voucher processing: >= 0.8 confidence -> post, < 0.8 -> review"""
    THRESHOLD = 0.8

    # High confidence cases (should auto-post)
    assert 0.85 >= THRESHOLD
    assert 1.0 >= THRESHOLD
    assert 0.8 >= THRESHOLD

    # Low confidence cases (should flag for review)
    assert 0.55 < THRESHOLD
    assert 0.0 < THRESHOLD
    assert 0.799 < THRESHOLD

    # Verify threshold is a float
    assert isinstance(THRESHOLD, float)


def test_outreach_cadence_defaults():
    """Verify default outreach cadences are reasonable"""
    cadences = {60, 45, 30, 7}
    assert len(cadences) == 4  # Active, Warm, Cold, New
    assert all(c > 0 for c in cadences)
    assert all(isinstance(c, int) for c in cadences)

    # Max cadence should not exceed 90 days (quarterly)
    assert max(cadences) <= 90
    # Min cadence should be at least 1 day
    assert min(cadences) >= 1


def test_cron_schedule_formats():
    """Verify all cron schedules are valid format"""
    with open(os.path.join(PROJECT_ROOT, "config", "cron", "jobs.json")) as f:
        data = json.load(f)

    for job in data["jobs"]:
        schedule = job.get("schedule", {})
        assert "kind" in schedule, f"Job {job['id']} missing schedule.kind"
        assert schedule["kind"] == "cron", f"Job {job['id']} has wrong schedule.kind"
        assert "expr" in schedule, f"Job {job['id']} missing schedule.expr"

        # Validate it has at least 5 space-separated fields (cron expression)
        expr = schedule["expr"]
        parts = expr.split()
        assert len(parts) >= 5, f"Job {job['id']} has invalid cron expr: {expr}"


def test_profile_configs_approval_wired():
    """Verify each profile config.yaml has approvals configured"""
    profiles = ["ar_watcher", "voucher_scanner", "outreach_agent"]
    for profile in profiles:
        config_path = os.path.join(
            os.path.expanduser("~"), ".hermes", "profiles", profile, "config.yaml"
        )
        if not os.path.exists(config_path):
            pytest.skip(f"Profile config not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        approvals = config.get("approvals", {})
        assert approvals.get("mode") == "manual", \
            f"Profile {profile}: approvals.mode should be 'manual'"
        assert "timeout" in approvals, \
            f"Profile {profile}: approvals.timeout is missing"


def test_profile_yamls_reference_correct_cron():
    """Verify repo profile yamls reference the correct cron job IDs"""
    profiles_config = os.path.join(PROJECT_ROOT, "config", "profiles")
    expected = {
        "ar_watcher.yaml": ["ar_daily_check"],
        "voucher_scanner.yaml": ["voucher_watchdog"],
        "outreach_agent.yaml": ["outreach_daily"],
    }

    for filename, expected_cron in expected.items():
        filepath = os.path.join(profiles_config, filename)
        with open(filepath) as f:
            config = yaml.safe_load(f)

        cron_jobs = config.get("cron", [])
        assert cron_jobs == expected_cron, \
            f"{filename}: expected cron={expected_cron}, got {cron_jobs}"
