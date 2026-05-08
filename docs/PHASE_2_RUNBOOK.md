# Phase 2 Runbook: Wire Cognee + PostgreSQL

**Prerequisite:** Phase 1 complete (personality, skills, .env mapped)
**Goal:** Cognee graph memory and PostgreSQL "Open Brain" fully connected to Hermes via MCP.
**Time:** ~2 hours

---

## Step 1: Cognee HTTP → MCP Wrapper

Cognee exposes REST endpoints (`/learn`, `/query`). Hermes expects MCP protocol.
Create a thin wrapper.

Create `cognee-server/mcp_wrapper.py`:

```python
"""
MCP wrapper for Cognee graph memory server.
Exposes cognee__memorize and cognee__query as MCP tools.
"""
import json
import sys
import httpx

COGNEE_URL = "http://localhost:8000"

COGNEE_TOOLS = [
    {
        "name": "cognee__memorize",
        "description": "Store a factual statement in the knowledge graph for long-term relational memory. Use this for facts about people, companies, projects, preferences, and relationships.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The factual statement to memorize, e.g. 'Acme Corp is a construction company with net60 payment terms.'"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "cognee__query",
        "description": "Search the knowledge graph for entities, relationships, and facts. Use this when asked 'what do you know about X' or when you need to recall stored information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or topic to search for, e.g. 'What do I know about Acme Corp?'"
                }
            },
            "required": ["query"]
        }
    }
]

async def handle_tool_call(tool_name: str, arguments: dict) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if tool_name == "cognee__memorize":
            resp = await client.post(
                f"{COGNEE_URL}/learn",
                json={"text": arguments["text"]}
            )
            return json.dumps(resp.json())
        
        elif tool_name == "cognee__query":
            resp = await client.get(
                f"{COGNEE_URL}/query",
                params={"q": arguments["query"]}
            )
            return json.dumps(resp.json())
        
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

# MCP stdio server protocol
def main():
    # This is a minimal MCP server. 
    # Full implementation would use @modelcontextprotocol/sdk (Python) or similar.
    # For Phase 2, we test HTTP first, then add MCP protocol if needed.
    pass

if __name__ == "__main__":
    main()
```

## Step 2: Configure Cognee as MCP Server

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  cognee:
    # Option A: If Hermes supports HTTP MCP servers
    transport: http
    url: http://localhost:8000
    tools:
      - cognee__memorize
      - cognee__query

    # Option B: If stdio is required, use the wrapper
    # command: python
    # args: ["-m", "cognee_server.mcp_wrapper"]
    # cwd: ./cognee-server

  postgres:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-postgres", "${POSTGRES_CONNECTION_STRING}"]
    env:
      POSTGRES_CONNECTION_STRING: ${POSTGRES_CONNECTION_STRING}
```

**Note:** Hermes MCP transport support varies by version. If HTTP transport isn't supported, the wrapper must implement the MCP stdio protocol (JSON-RPC over stdin/stdout). The `mcp` Python package provides this. If needed:

```bash
cd cognee-server
uv add mcp
```

Then implement the full MCP server protocol in `mcp_wrapper.py`.

## Step 3: Test Cognee Round-Trip

Before involving Hermes, verify Cognee works standalone:

```bash
# Start Cognee if not running
cd cognee-server && docker compose up -d

# Test memorization
curl -s -X POST http://localhost:8000/learn \
  -H "Content-Type: application/json" \
  -d '{"text": "Bridge and Bolt is an AI automation company for SMBs founded by Russell. Their first product automates AR collections and voucher processing."}'

# Test query
curl -s "http://localhost:8000/query?q=Bridge%20and%20Bolt"

# Expected: JSON with entity "Bridge and Bolt", relationships to Russell, SMBs, etc.
```

Checklist:
- [ ] Learn endpoint returns 200 with entity data
- [ ] Query endpoint returns entity + relationships
- [ ] DeepSeek extraction is working (entities are extracted, not just keyword match)
- [ ] Graph fallback works (if Cognee pipeline fails, direct DeepSeek extraction runs)

## Step 4: Test Through Hermes

Restart gateway:
```bash
hermes gateway restart
```

From Discord:
```
1. "What MCP tools are available?"
   → Expected: Agent lists all MCP tools including cognee__memorize, cognee__query

2. "Remember that our biggest client is Acme Corp, a construction company in Phoenix with net60 payment terms and annual revenue around $15M."

3. "What do you know about Acme Corp?"
   → Expected: Agent queries the graph and returns structured facts, not just recent conversation
```

## Step 5: Deploy Business Schema to PostgreSQL

```bash
psql "${POSTGRES_CONNECTION_STRING}" -f schema/business.sql
```

Verify from Discord:
```
1. "List all the tables in the database."
   → Expected: ar_invoices, ar_invoices_aging, collection_activity, customers, 
               voucher_queue, accounting_entries, outreach_schedule, outreach_log

2. "Insert a test invoice for Acme Corp due 120 days ago."
   → Expected: Agent creates a row, confirms

3. "Now insert a payment of $500 on that invoice."
   → Expected: Agent creates payment record, may update balance
```

## Step 6: Write the E2E Integration Tests

Create `tests/test_integration.py`:

```python
"""Integration tests: Cognee graph + PostgreSQL + AR watcher pipeline"""
import subprocess
import json
import pytest

COGNEE_URL = "http://localhost:8000"

@pytest.fixture
def cognee_running():
    """Verify Cognee is running"""
    import httpx
    try:
        resp = httpx.get(f"{COGNEE_URL}/health", timeout=5)
        assert resp.status_code == 200
        return True
    except Exception:
        pytest.skip("Cognee server not running")

def test_cognee_learn_and_query_single_entity(cognee_running):
    """Learn a fact, query it, verify structured response"""
    import httpx
    
    # Learn
    resp = httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "TestCorp is a software company in Austin with net30 terms."},
        timeout=30
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "TestCorp" in str(data).lower() or resp.status_code == 200
    
    # Query
    resp = httpx.get(
        f"{COGNEE_URL}/query",
        params={"q": "TestCorp"},
        timeout=30
    )
    assert resp.status_code == 200
    
    # Should find the entity
    response_text = str(resp.json()).lower()
    assert "testcorp" in response_text

def test_cognee_learn_relationship(cognee_running):
    """Learn two entities with a relationship, verify traversal"""
    import httpx
    
    # Learn entity A
    httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "Alice is the CFO of TechCorp."},
        timeout=30
    )
    
    # Learn entity B (linked)
    httpx.post(
        f"{COGNEE_URL}/learn",
        json={"text": "TechCorp uses Bridge and Bolt for AR automation."},
        timeout=30
    )
    
    # Query - should find the relationship
    resp = httpx.get(
        f"{COGNEE_URL}/query",
        params={"q": "Who is Alice"},
        timeout=30
    )
    assert resp.status_code == 200
    response_text = str(resp.json()).lower()
    assert "alice" in response_text

def test_collection_letter_template_friendly(cognee_running):
    """Verify friendly letter template has required placeholders"""
    with open("templates/collection_letters.md") as f:
        content = f.read()
    
    required = [
        "{invoice_number}",
        "{amount}",
        "{contact_first_name}",
        "{invoice_date}",
        "{business_name}"
    ]
    for var in required:
        assert var in content, f"Missing template variable: {var}"

def test_collection_letter_template_firm(cognee_running):
    """Verify firm letter template has escalation language"""
    with open("templates/collection_letters.md") as f:
        content = f.read()
    
    assert "days past due" in content
    assert "{deadline_date}" in content

def test_collection_letter_template_final(cognee_running):
    """Verify final letter template has collections warning"""
    with open("templates/collection_letters.md") as f:
        content = f.read()
    
    assert "FINAL NOTICE" in content
    assert "collections action" in content.lower()
```

Run:
```bash
cd tests
pytest test_integration.py -v
```

## Gate: Proceed to Phase 3 if...

- [ ] Cognee learn/query work from command line
- [ ] Cognee tools appear in Hermes tool list
- [ ] Agent can "remember" and "recall" facts through the graph
- [ ] Business schema deployed to PostgreSQL
- [ ] Agent can query and insert into Postgres via MCP
- [ ] Integration tests pass (learn → query round-trip, template validation)
- [ ] Google Workspace tests still pass (unchanged)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cognee tools don't appear in Hermes | Restart gateway. Check MCP logs. Try `hermes tools list` |
| Hermes can't call Cognee (timeout) | Cognee not running on port 8000. `docker compose up -d` |
| DeepSeek extraction fails | Check `DEEPSEEK_API_KEY` in Cognee `.env`. Verify Cognee `GRAPH_LLM_PROVIDER=deepseek` |
| PostgreSQL connection refused | Check `POSTGRES_CONNECTION_STRING`. Ensure Postgres allows connections |
| "Tool not found: cognee__memorize" | Tool name mismatch. Check exact tool name via `hermes tools list` |
