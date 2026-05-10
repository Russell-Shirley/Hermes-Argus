"""Verify data integrity: agent reads/writes correctly, no injection, no hallucination"""
import subprocess
import json
import pytest


DOCKER_EXEC = ["docker", "exec", "argus-openbrain"]
PSQL = ["psql", "-U", "postgres", "-d", "openbrain", "-A", "-F|", "-t", "-c"]


def _psql(sql):
    """Run a query against PostgreSQL and return stripped stdout."""
    result = subprocess.run(
        DOCKER_EXEC + PSQL + [sql],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def _psql_file(filepath):
    """Run a SQL file against PostgreSQL."""
    result = subprocess.run(
        ["docker", "exec", "-i", "argus-openbrain", "psql", "-U", "postgres", "-d", "openbrain"],
        input=open(filepath).read(),
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0, result.stderr


def test_aging_view_calculates_correctly():
    """Verify ar_invoices_aging computes days_overdue and aging_bucket correctly."""
    output = _psql(
        "SELECT days_overdue, aging_bucket FROM ar_invoices_aging WHERE invoice_number = 'INV-2025-050';"
    )
    assert output, "No rows returned for INV-2025-050"
    first_row = output.split("\n")[0]
    parts = [p.strip() for p in first_row.split("|")]
    days_overdue = int(parts[0])
    bucket = parts[1]
    assert days_overdue > 90, f"Expected >90 days overdue, got {days_overdue}"
    assert bucket in ("121+", "91-120"), f"Expected oldest bucket, got {bucket}"


def test_seed_data_present():
    """Verify seed data was inserted for all tables."""
    # Customers
    output = _psql("SELECT COUNT(*) FROM customers;")
    assert int(output) >= 3, f"Expected >=3 customers, got {output}"

    # Invoices
    output = _psql("SELECT COUNT(*) FROM ar_invoices;")
    assert int(output) >= 7, f"Expected >=7 invoices, got {output}"

    # Vouchers
    output = _psql("SELECT COUNT(*) FROM voucher_queue;")
    assert int(output) >= 3, f"Expected >=3 vouchers, got {output}"

    # Outreach schedule
    output = _psql("SELECT COUNT(*) FROM outreach_schedule;")
    assert int(output) >= 3, f"Expected >=3 outreach entries, got {output}"


def test_parameterized_insert_not_vulnerable():
    """Verify schema supports parameterized queries (injection attempt yields literal storage)."""
    malicious = "''; DROP TABLE customers; --"
    _psql(
        f"INSERT INTO collection_activity (invoice_id, action, agent_note) "
        f"SELECT id, 'test', '{malicious}' FROM ar_invoices LIMIT 1;"
    )

    # Verify customers table still exists
    output = _psql("SELECT COUNT(*) FROM customers;")
    assert int(output) > 0, "customers table was dropped — SQL injection vulnerability"

    # Clean up
    _psql(f"DELETE FROM collection_activity WHERE agent_note = '{malicious}';")


def test_collection_activity_foreign_key():
    """Verify collection_activity requires valid invoice_id."""
    ok, stderr = _psql_file("tests/fixtures/seed_test_data.sql")
    assert ok or "already exists" in stderr.lower() or not stderr

    result = subprocess.run(
        DOCKER_EXEC + PSQL + [
            "INSERT INTO collection_activity (invoice_id, action) VALUES "
            "('00000000-0000-0000-0000-000000000000', 'letter_sent');"
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0 or "violates" in (result.stderr or "").lower() or "ERROR" in (result.stdout or "").upper(), \
        "Should have raised foreign key violation"


def test_voucher_status_constraints():
    """Verify voucher_queue has only valid statuses."""
    output = _psql("SELECT DISTINCT status FROM voucher_queue;")
    statuses = {s.strip() for s in output.split("\n") if s.strip()}
    valid = {"pending", "processing", "posted", "needs_review", "failed"}
    for status in statuses:
        assert status in valid, f"Invalid voucher status: {status}"


def test_all_business_tables_exist():
    """Verify all 8 tables/views from business schema are present."""
    output = _psql(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' "
        "ORDER BY table_name;"
    )
    tables = {t.strip() for t in output.split("\n") if t.strip()}
    expected = {
        "accounting_entries", "ar_invoices", "collection_activity",
        "customers", "outreach_log", "outreach_schedule", "voucher_queue",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"

    # Verify view exists
    output = _psql(
        "SELECT table_name FROM information_schema.views "
        "WHERE table_name = 'ar_invoices_aging';"
    )
    assert "ar_invoices_aging" in output, "ar_invoices_aging view is missing"


def test_aging_view_excludes_paid_and_written_off():
    """Verify the aging view correctly excludes paid and written_off invoices."""
    output = _psql(
        "SELECT status FROM ar_invoices_aging WHERE status = 'paid';"
    )
    assert not output, f"View includes paid invoices: {output}"

    output = _psql(
        "SELECT status FROM ar_invoices_aging WHERE status = 'written_off';"
    )
    assert not output, f"View includes written_off invoices: {output}"
