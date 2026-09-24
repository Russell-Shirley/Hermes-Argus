"""Behavior tests for analyze_qualify.py — run identity + per-run exclusions.

Both of these were baked-in Cumming values in a toolkit that serves every city:
the report header said "Cumming GA" (so the next city's report was mislabelled)
and the exclusion list carried one city's call-out into every other run.
"""
import json
import os
import subprocess
import sys

import pytest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(KIT, "analyze_qualify.py")


def rec(**over):
    """A qualify_merged record that qualifies: zero owner replies on recent positives."""
    base = {
        "rank": 9, "name": "Silent Duct Co", "phone": "(770) 555-0000",
        "rating": "4.9", "reviews": "120", "status": "OK",
        "sample_size": 5, "newest_review_days": 14, "reviews_last_180d": 5,
        "reviews_last_365d": 5, "recent_n": 5, "recent_positive_n": 5,
        "owner_responses_recent": 0, "response_rate_recent": 0,
        "sorted_newest": True,
    }
    base.update(over)
    return base


def run(tmp_path, records, argv=(), exclusions=None, feed=None):
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "qualify_merged.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    if exclusions is not None:
        (data / "exclusions.json").write_text(json.dumps(exclusions), encoding="utf-8")
    if feed is not None:
        (data / "ranked-feed.json").write_text(json.dumps(feed), encoding="utf-8")
    env = dict(os.environ, RUN_DATA=str(data))
    p = subprocess.run([sys.executable, SCRIPT, *argv], env=env,
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    report = (data / "qualify_report.md").read_text(encoding="utf-8")
    return data, report, p.stdout


def test_report_names_the_run_that_produced_it(tmp_path):
    """The header carries this run's area label and actual rank span, not another city's."""
    _, report, _ = run(tmp_path, [rec(rank=11), rec(rank=47, name="Other Duct Co")],
                       argv=["--area-label=canton-ga"])
    assert "Canton-GA" in report
    assert "ranks 11-47" in report
    assert "Cumming" not in report


def test_report_falls_back_to_a_generic_title_without_a_label(tmp_path):
    _, report, _ = run(tmp_path, [rec()])
    assert "Cumming" not in report
    assert "rank span" in report or "ranks 9-9" in report


def test_run_exclusions_come_from_the_run_not_the_toolkit(tmp_path):
    """A name in <run>/data/exclusions.json is excluded even with a perfect fit."""
    _, report, _ = run(tmp_path, [rec(name="Do Not Contact LLC")],
                       argv=["--area-label=canton-ga"],
                       exclusions={"names": ["Do Not Contact LLC"]})
    assert "Do Not Contact LLC" in report
    assert "EXCLUDE (already responds)" in report
    assert "QUALIFIED" not in report


def test_no_exclusions_file_means_no_silent_exclusions(tmp_path):
    """Without the file, nothing is dropped for a reason the run never stated."""
    data, report, _ = run(tmp_path, [rec(name="Any Duct Co")], argv=["--area-label=canton-ga"])
    assert not (data / "exclusions.json").exists()
    assert "QUALIFIED - PRIORITY" in report


def test_unreadable_exclusions_file_warns_instead_of_crashing(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "qualify_merged.jsonl").write_text(json.dumps(rec()) + "\n", encoding="utf-8")
    (data / "exclusions.json").write_text("{not json", encoding="utf-8")
    env = dict(os.environ, RUN_DATA=str(data))
    p = subprocess.run([sys.executable, SCRIPT, "--area-label=canton-ga"], env=env,
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "WARNING" in p.stdout


@pytest.mark.parametrize("status,expect", [
    ("GATED", "NO DATA (reviews gated — rerun)"),
    ("ERROR", "NO DATA (capture errored — rerun)"),
])
def test_an_unmeasured_row_is_never_scored_as_a_thin_sample(tmp_path, status, expect):
    """A gate and a transport error both mean 'not seen'; neither is a zero, and neither
    may fall through to a verdict that reads like a measurement."""
    _, report, _ = run(tmp_path, [rec(status=status, response_rate_recent=None,
                                      recent_positive_n=0, owner_responses_recent=0)],
                       argv=["--area-label=canton-ga"])
    assert expect in report
    assert "REVIEW MORE" not in report
    assert "QUALIFIED" not in report
