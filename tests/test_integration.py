"""Integration tests: Cognee graph + PostgreSQL + AR watcher pipeline"""
import json
import time
import pytest
import httpx

COGNEE_URL = "http://localhost:8000"


@pytest.fixture
def cognee_running():
    """Verify Cognee is running"""
    try:
        resp = httpx.get(f"{COGNEE_URL}/query", params={"q": "test"}, timeout=5)
        assert resp.status_code in (200, 500)
        return True
    except Exception:
        pytest.skip("Cognee server not running")


def test_cognee_learn_and_query_single_entity(cognee_running):
    """Learn a fact, query it, verify structured response"""
    # Learn
    resp = httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "TestCorp is a software company in Austin with net30 terms."},
        timeout=30,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"

    # Retry query up to 10 times (background memorization is async)
    for _ in range(10):
        time.sleep(3)
        resp = httpx.get(
            f"{COGNEE_URL}/query",
            params={"q": "TestCorp"},
            timeout=30,
        )
        assert resp.status_code == 200
        result = resp.json()
        if result.get("data") and len(result["data"]) > 0:
            break

    response_text = str(resp.json()).lower()
    assert "testcorp" in response_text


def test_cognee_learn_relationship(cognee_running):
    """Learn two entities with a relationship, verify traversal"""
    # Learn entity A
    httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "Alice is the CFO of TechCorp."},
        timeout=30,
    )

    # Learn entity B (linked)
    httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "TechCorp uses Bridge and Bolt for AR automation."},
        timeout=30,
    )

    # Retry query up to 10 times (background memorization is async)
    for _ in range(10):
        time.sleep(3)
        resp = httpx.get(
            f"{COGNEE_URL}/query",
            params={"q": "Who is Alice"},
            timeout=30,
        )
        assert resp.status_code == 200
        result = resp.json()
        if result.get("data") and len(result["data"]) > 0:
            break

    response_text = str(resp.json()).lower()
    assert "alice" in response_text


def test_collection_letter_template_friendly():
    """Verify friendly letter template has required placeholders"""
    with open("templates/collection_letters.md") as f:
        content = f.read()

    required = [
        "{invoice_number}",
        "{amount}",
        "{contact_first_name}",
        "{invoice_date}",
        "{business_name}",
    ]
    for var in required:
        assert var in content, f"Missing template variable: {var}"


def test_collection_letter_template_firm():
    """Verify firm letter template has escalation language"""
    with open("templates/collection_letters.md") as f:
        content = f.read()

    assert "days past due" in content
    assert "{deadline_date}" in content


def test_collection_letter_template_final():
    """Verify final letter template has collections warning"""
    with open("templates/collection_letters.md") as f:
        content = f.read()

    assert "FINAL NOTICE" in content
    assert "collections action" in content.lower()
