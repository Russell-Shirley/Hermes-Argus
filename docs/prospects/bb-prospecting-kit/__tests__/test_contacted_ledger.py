"""Tests for contacted_ledger: cross-city matching must never merge or skip look-alike names.

Ported to the per-vertical ledger API (one file per niche, `--niche` required for
seed/check/mark). Every assertion from the original suite is kept.
"""
import argparse
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import contacted_ledger as cl  # noqa: E402

NICHE = "duct-cleaning"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """Point the kit at an empty ledger DIRECTORY (one <niche>.jsonl inside)."""
    monkeypatch.setattr(cl, "LEDGER_DIR", str(tmp_path))
    return tmp_path


def seed(name, phone, area, outcome, niche=NICHE):
    recs = cl.load(niche)
    cl.upsert(recs, name, phone, area, niche, "run", outcome)
    cl.save(niche, recs)


def write_feed(tmp_path, entries):
    p = tmp_path / "ranked-feed.json"
    p.write_text(json.dumps({"maps_full": entries}), encoding="utf-8")
    return str(p)


def mark_args(**kw):
    d = dict(name="", phone="", status="contacted", sender="s1", channel="email", arm="",
             date="2026-09-23", notes="", area="", niche=NICHE, create=False, force=False)
    d.update(kw)
    return argparse.Namespace(**d)


def test_selftest_passes(ledger):
    assert cl.cmd_selftest(None) == 0


def test_check_flags_name_only_match_even_when_contacted(ledger, tmp_path, capsys):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "contacted")
    feed = write_feed(tmp_path, [{"local_rank": 3, "name": "H&M Services", "phone": "(678) 999-8888"}])
    cl.cmd_check(argparse.Namespace(feed=feed, area="alpharetta-ga", niche=NICHE))
    out = capsys.readouterr().out
    assert "FLAG" in out
    assert not (tmp_path / "seen-skip.txt").read_text(encoding="utf-8").strip()


def test_check_skips_phone_match_across_areas(ledger, tmp_path):
    seed("Air of America", "7708003152", "cumming-ga", "contacted")
    feed = write_feed(tmp_path, [{"local_rank": 1, "name": "Air of America LLC", "phone": "(770) 800-3152"}])
    assert cl.cmd_check(argparse.Namespace(feed=feed, area="alpharetta-ga", niche=NICHE)) == 3  # nothing new
    assert "phone" in (tmp_path / "seen-skip.txt").read_text(encoding="utf-8")


def test_mark_does_not_touch_same_name_in_other_area(ledger):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "qualified")
    rc = cl.cmd_mark(mark_args(name="H&M Services", area="alpharetta-ga"))
    assert rc == 2  # not found, nothing written
    assert cl.load(NICHE)[0]["outcome"] == "qualified"


def test_mark_matches_by_phone_and_area(ledger):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "qualified")
    assert cl.cmd_mark(mark_args(name="H & M Services", phone="4701112222")) == 0
    assert cl.load(NICHE)[0]["outcome"] == "contacted"
    seed("Bobs Vents", "", "cumming-ga", "qualified")
    assert cl.cmd_mark(mark_args(name="Bobs Vents", area="cumming-ga")) == 0


def test_mark_refuses_downgrade_without_force(ledger):
    seed("Tester Co", "4045551212", "cumming-ga", "replied")
    assert cl.cmd_mark(mark_args(name="Tester Co", phone="4045551212", status="contacted")) == 4
    assert cl.load(NICHE)[0]["outcome"] == "replied"


def test_load_empty_or_missing_ledger(ledger):
    assert cl.load(NICHE) == []


# ── per-vertical ledgers: the reason the split exists ────────────────────────

def test_each_vertical_gets_its_own_file(ledger):
    seed("Tester Co", "4045551212", "cumming-ga", "excluded")
    seed("Bobs Septic", "7705550000", "cumming-ga", "qualified", niche="septic")
    assert cl.ledger_niches() == ["duct-cleaning", "septic"]
    assert cl.ledger_path("duct-cleaning") != cl.ledger_path("septic")


def test_same_business_holds_independent_outcomes_per_vertical(ledger):
    # An exclusion in one vertical must not colour the other: the offers differ.
    seed("Tester Co", "4045551212", "cumming-ga", "excluded")
    seed("Tester Co", "4045551212", "cumming-ga", "qualified", niche="septic")
    assert cl.load("duct-cleaning")[0]["outcome"] == "excluded"
    assert cl.load("septic")[0]["outcome"] == "qualified"


def test_marking_one_vertical_leaves_the_other_untouched(ledger):
    seed("Tester Co", "4045551212", "cumming-ga", "qualified")
    seed("Tester Co", "4045551212", "cumming-ga", "qualified", niche="septic")
    assert cl.cmd_mark(mark_args(name="Tester Co", phone="4045551212", status="contacted")) == 0
    assert cl.load("duct-cleaning")[0]["outcome"] == "contacted"
    assert cl.load("septic")[0]["outcome"] == "qualified"


def test_check_reports_other_vertical_as_info_not_skip(ledger, tmp_path, capsys):
    # Known from septic only → still in scope for this duct-cleaning run.
    seed("Dual Service Co", "7705559999", "cumming-ga", "contacted", niche="septic")
    feed = write_feed(tmp_path, [{"local_rank": 5, "name": "Dual Service Co", "phone": "(770) 555-9999"}])
    assert cl.cmd_check(argparse.Namespace(feed=feed, area="cumming-ga", niche=NICHE)) == 0  # NEW exists
    out = capsys.readouterr().out
    assert "INFO" in out and "septic" in out
    assert not (tmp_path / "seen-skip.txt").read_text(encoding="utf-8").strip()


def test_niche_slug_is_normalised(ledger):
    seed("Tester Co", "4045551212", "cumming-ga", "qualified", niche="Duct Cleaning")
    assert cl.ledger_niches() == ["duct-cleaning"]
    assert cl.load("duct_cleaning")[0]["niche"] == "duct-cleaning"
