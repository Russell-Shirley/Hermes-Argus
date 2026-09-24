"""Tests for contacted_ledger: cross-city matching must never merge or skip look-alike names."""
import argparse
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import contacted_ledger as cl  # noqa: E402


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "contacted.jsonl"
    monkeypatch.setattr(cl, "LEDGER", str(path))
    return path


def seed(name, phone, area, outcome):
    recs = cl.load()
    cl.upsert(recs, name, phone, area, "duct-cleaning", "run", outcome)
    cl.save(recs)


def write_feed(tmp_path, entries):
    p = tmp_path / "ranked-feed.json"
    p.write_text(json.dumps({"maps_full": entries}), encoding="utf-8")
    return str(p)


def mark_args(**kw):
    d = dict(name="", phone="", status="contacted", sender="s1", channel="email", arm="",
             date="2026-09-23", notes="", area="", niche="", create=False, force=False)
    d.update(kw)
    return argparse.Namespace(**d)


def test_selftest_passes(ledger):
    assert cl.cmd_selftest(None) == 0


def test_check_flags_name_only_match_even_when_contacted(ledger, tmp_path, capsys):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "contacted")
    feed = write_feed(tmp_path, [{"local_rank": 3, "name": "H&M Services", "phone": "(678) 999-8888"}])
    cl.cmd_check(argparse.Namespace(feed=feed, area="alpharetta-ga"))
    out = capsys.readouterr().out
    assert "FLAG" in out
    assert not (tmp_path / "seen-skip.txt").read_text(encoding="utf-8").strip()


def test_check_skips_phone_match_across_areas(ledger, tmp_path):
    seed("Air of America", "7708003152", "cumming-ga", "contacted")
    feed = write_feed(tmp_path, [{"local_rank": 1, "name": "Air of America LLC", "phone": "(770) 800-3152"}])
    assert cl.cmd_check(argparse.Namespace(feed=feed, area="alpharetta-ga")) == 3  # nothing new
    assert "phone" in (tmp_path / "seen-skip.txt").read_text(encoding="utf-8")


def test_mark_does_not_touch_same_name_in_other_area(ledger):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "qualified")
    rc = cl.cmd_mark(mark_args(name="H&M Services", area="alpharetta-ga"))
    assert rc == 2  # not found, nothing written
    assert cl.load()[0]["outcome"] == "qualified"


def test_mark_matches_by_phone_and_area(ledger):
    seed("H & M Services", "(470) 111-2222", "cumming-ga", "qualified")
    assert cl.cmd_mark(mark_args(name="H & M Services", phone="4701112222")) == 0
    assert cl.load()[0]["outcome"] == "contacted"
    seed("Bobs Vents", "", "cumming-ga", "qualified")
    assert cl.cmd_mark(mark_args(name="Bobs Vents", area="cumming-ga")) == 0


def test_mark_refuses_downgrade_without_force(ledger):
    seed("Tester Co", "4045551212", "cumming-ga", "replied")
    assert cl.cmd_mark(mark_args(name="Tester Co", phone="4045551212", status="contacted")) == 4
    assert cl.load()[0]["outcome"] == "replied"


def test_load_empty_or_missing_ledger(ledger):
    assert cl.load() == []
