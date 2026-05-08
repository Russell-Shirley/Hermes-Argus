# Phase 0 Runbook: Hermes-Argus Proof of Life

**Goal:** Prove the architecture works end-to-end before building more modules.
**Time:** ~2 hours

---

## Step 1: Install Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes --version
```

## Step 2: Run Setup Wizard

```bash
hermes setup
```

During setup:
- Choose DeepSeek as primary provider (add API key from Argus `.env`)
- Add Ollama for local/background (endpoint: `http://localhost:11434/v1`)
- Enable Discord gateway
- Set Discord bot token and allowed user IDs (from Argus `.env`)
- Choose personality (pick one for now, we'll replace it later)

## Step 3: Verify Discord Works

```bash
hermes gateway start
```

Send a message to your Discord bot. Confirm:
- [ ] Bot responds
- [ ] Responses use the correct personality
- [ ] `/new` resets conversation
- [ ] `/model` shows available providers

## Step 4: Verify Ollama (Free Local LLM)

```bash
# Make sure Ollama is running
ollama list
ollama run gemma4:9b "Hello, this is a test."
```

Then in Discord, switch to local model:
```
/model ollama/gemma4:9b
"Test message"
```

Confirm:
- [ ] Local model responds (no API cost)
- [ ] Response quality is acceptable for background tasks

## Step 5: Start Cognee Sidecar

```bash
cd cognee-server
docker compose up -d
# Wait 10 seconds for startup
curl http://localhost:8000/health
```

Test Cognee directly:
```bash
# Learn a fact
curl -X POST http://localhost:8000/learn \
  -H "Content-Type: application/json" \
  -d '{"text": "Russell founded Bridge and Bolt in 2024. The company builds AI automation for SMBs."}'

# Query it back
curl "http://localhost:8000/query?q=Bridge%20and%20Bolt"

# Expected: JSON response with entity/relationship data
```

## Step 6: Wire Cognee as Hermes MCP Server

Edit `~/.hermes/config.yaml`, add under `mcp_servers`:

```yaml
mcp_servers:
  cognee:
    transport: http
    url: http://localhost:8000
    tools:
      - cognee__memorize
      - cognee__query
```

Or if Hermes exposes MCP endpoints as tools:
```yaml
mcp_servers:
  cognee:
    command: "./cognee-server/mcp_wrapper.py"  # Create this if needed
    # OR use HTTP:
    # transport: http
    # url: http://localhost:8000
```

Restart gateway:
```bash
hermes gateway restart
```

Test from Discord:
```
Remember that Acme Corp is a construction company with 90-day payment terms.
```
Then:
```
What do you know about Acme Corp?
```

Confirm:
- [ ] Agent triggers memory storage (calls cognee tool)
- [ ] Query returns the stored fact
- [ ] Response references the graph data, not just recent conversation

## Step 7: Wire PostgreSQL MCP

Edit `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  postgres:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-postgres", "${POSTGRES_CONNECTION_STRING}"]
    env:
      POSTGRES_CONNECTION_STRING: ${POSTGRES_CONNECTION_STRING}
```

Run schema:
```bash
psql $POSTGRES_CONNECTION_STRING -f schema/business.sql
```

Test from Discord:
```
List all tables in the database.
```

## Step 8: Deploy AR Watcher Profile

Copy personality and config:
```bash
mkdir -p ~/.hermes/profiles/ar_watcher
cp config/profiles/ar_watcher.md ~/.hermes/profiles/ar_watcher/
cp config/profiles/ar_watcher.yaml ~/.hermes/profiles/ar_watcher/
```

Install skills:
```bash
hermes skills install --dir modules/icm_base
hermes skills install --dir modules/ar_collections
```

Insert test data via psql or Hermes:
```sql
INSERT INTO customers (name, contact_name, payment_terms) 
VALUES ('Test Corp', 'John Doe', 'net30');

INSERT INTO ar_invoices (customer_name, invoice_number, invoice_date, due_date, amount, balance, status) 
VALUES ('Test Corp', 'INV-001', '2026-02-01', '2026-02-14', 5000.00, 5000.00, 'open');
```

Test from Discord (switch to AR watcher profile):
```
Check for overdue invoices.
```

Confirm:
- [ ] Agent queries `ar_invoices` table
- [ ] Identifies the overdue invoice
- [ ] Generates a draft collection letter
- [ ] Does NOT send without approval

## Step 9: Run Existing Tests

```bash
# Google Workspace MCP tests (51 tests)
cd google-tools
uv run pytest google_tools/__tests__/ -v

# Cognee adapter tests
cd ../cognee-server
python test_adapter.py
python test_cognee_client.py
```

Confirm:
- [ ] All Google Workspace tests pass
- [ ] Cognee learn/query round-trip works
- [ ] Tests are framework-independent (they don't import Hermes or Argus)

## Step 10: Write E2E Smoke Test

Create `tests/test_e2e_ar_watcher.py`:

```python
"""End-to-end smoke test: AR watcher profile → Cognee graph → Postgres"""
import subprocess
import json
import pytest

def test_cognee_round_trip():
    """Learn a fact, query it back, verify entity extraction"""
    # Learn
    resp = subprocess.run([
        "curl", "-s", "-X", "POST", "http://localhost:8000/learn",
        "-H", "Content-Type: application/json",
        "-d", '{"text": "Acme Corp is a construction company in Phoenix with net60 terms."}'
    ], capture_output=True, text=True)
    assert resp.returncode == 0
    
    # Query
    resp = subprocess.run([
        "curl", "-s", "http://localhost:8000/query?q=Acme+Corp"
    ], capture_output=True, text=True)
    
    data = json.loads(resp.stdout)
    assert "Acme Corp" in str(data)
    # Should find entity and relationships

def test_schema_exists():
    """Verify business schema is deployed"""
    # This assumes PostgreSQL is accessible
    # Replace with actual connection test
    pass

def test_collection_letter_template():
    """Verify all three letter templates parse correctly"""
    with open("templates/collection_letters.md") as f:
        content = f.read()
    assert "ar_collection_letter_friendly" in content
    assert "ar_collection_letter_firm" in content
    assert "ar_collection_letter_final" in content
```

Run:
```bash
pytest tests/ -v
```

## Gate: Proceed to Phase 1 if...

- [ ] Discord bot responds
- [ ] Cognee learn → query round-trip works
- [ ] PostgreSQL MCP connected
- [ ] AR watcher queries invoices and generates draft letters
- [ ] Google Workspace tests pass (51 passes)
- [ ] Cognee adapter tests pass
- [ ] All 3 collection letter templates parse

## Windows-Specific Notes

- Install via `pip install hermes-agent` (not curl|bash)
- `hermes setup --non-interactive` may crash with UnicodeEncodeError — use `hermes config set` instead
- `hermes gateway stop` fails (Unix signal) — use `Stop-Process -Id <pid>` or Task Manager
- `hermes skills install --dir` doesn't exist in v0.10 — copy ICM modules to skill directories manually
- Use `curl.exe` not `curl` (PowerShell alias conflict)
- Cognee `/health` doesn't exist — use `/query?q=test` or `/docs`

## If Something Fails

| Symptom | Likely fix |
|---------|-----------|
| Hermes can't call Cognee | Cognee exposes HTTP, not MCP — may need a thin MCP wrapper script. Write `cognee-server/mcp_wrapper.py` |
| PostgreSQL MCP rejects connection | `POSTGRES_CONNECTION_STRING` not in env. Add to `~/.hermes/.env` |
| AR watcher can't find schema | Schema not deployed. Run `schema/business.sql` |
| Google Workspace tests fail on Windows | venv in wrong Python. Use `uv run` (handles this) |
| Ollama slow on first call | Expected — cold start. Run `ollama run gemma4:e4b "warmup"` once |
| `ar_invoices` fails: relation "customers" does not exist | Schema ordering issue. Run `customers` block first in `business.sql` |
| Cognee client tests hang | DeepSeek API call timing out. Verify HTTP round-trip via `/learn` + `/query` instead |
| `hermes config set env.KEY` errors | Env vars go in `~/.hermes/.env` file, not via `config set` |
