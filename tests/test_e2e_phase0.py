"""End-to-end smoke test: Cognee graph, PostgreSQL schema, collection letter templates."""
import subprocess
import json
import time
import pytest

COGNEE_URL = "http://localhost:8000"


def test_cognee_round_trip():
    """Learn a fact, query it back, verify entity extraction."""
    text = "Acme Corp is a construction company in Phoenix with net60 terms."

    # Learn
    resp = subprocess.run(
        [
            "curl.exe", "-s", "-X", "POST", f"{COGNEE_URL}/learn",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"text": text}),
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert resp.returncode == 0, f"learn failed: {resp.stderr}"
    data = json.loads(resp.stdout)
    assert data["status"] == "queued"

    # Retry query up to 10 times (background memorization is async)
    for attempt in range(10):
        time.sleep(3)
        resp = subprocess.run(
            ["curl.exe", "-s", f"{COGNEE_URL}/query?q=Acme+Corp"],
            capture_output=True, text=True, timeout=30,
        )
        assert resp.returncode == 0, f"query failed: {resp.stderr}"
        data = json.loads(resp.stdout)
        assert data["status"] == "success"
        if data.get("data") and len(data["data"]) > 0:
            break

    assert data.get("data"), f"Query returned no data after 10 retries: {data}"
    assert "Acme Corp" in str(data)


def test_schema_exists():
    """Verify business schema tables exist in PostgreSQL."""
    result = subprocess.run(
        ["docker", "exec", "argus-openbrain", "psql", "-U", "postgres", "-d", "openbrain",
         "-t", "-c",
         "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('customers','ar_invoices','collection_activity','voucher_queue','accounting_entries','outreach_schedule','outreach_log') ORDER BY table_name;"],
        capture_output=True, text=True, timeout=30,
    )
    tables = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
    expected = {"accounting_entries", "ar_invoices", "collection_activity", "customers",
                "outreach_log", "outreach_schedule", "voucher_queue"}
    assert len(tables) == 7, f"Expected 7 tables, found {len(tables)}: {tables}"
    assert set(tables) == expected


def test_ar_invoices_aging_view():
    """Verify the aging view returns expected columns."""
    result = subprocess.run(
        ["docker", "exec", "argus-openbrain", "psql", "-U", "postgres", "-d", "openbrain",
         "-t", "-c",
         "SELECT column_name FROM information_schema.columns WHERE table_name='ar_invoices_aging' ORDER BY ordinal_position;"],
        capture_output=True, text=True, timeout=30,
    )
    cols = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
    assert "days_overdue" in cols
    assert "aging_bucket" in cols


def test_collection_letter_templates():
    """Verify all three letter templates parse correctly."""
    with open("templates/collection_letters.md") as f:
        content = f.read()
    assert "ar_collection_letter_friendly" in content
    assert "ar_collection_letter_firm" in content
    assert "ar_collection_letter_final" in content


def test_test_data_inserted():
    """Verify the runbook test data is present."""
    result = subprocess.run(
        ["docker", "exec", "argus-openbrain", "psql", "-U", "postgres", "-d", "openbrain",
         "-t", "-c",
         "SELECT customer_name, invoice_number, balance FROM ar_invoices WHERE invoice_number='INV-001';"],
        capture_output=True, text=True, timeout=30,
    )
    assert "Test Corp" in result.stdout
    assert "INV-001" in result.stdout
    assert "5000.00" in result.stdout


def test_cognee_server_responding():
    """Verify Cognee HTTP server is reachable."""
    resp = subprocess.run(
        ["curl.exe", "-s", "-o", "nul", "-w", "%{http_code}", COGNEE_URL + "/query?q=test"],
        capture_output=True, text=True, timeout=30,
    )
    assert resp.stdout.strip() in ("200", "500"), f"Unexpected status: {resp.stdout}"
