# Phase 4 Runbook: Multi-Agent Profiles

**Prerequisite:** Phase 3 complete (PostgreSQL wired, agent reads/writes business data)
**Goal:** Three independent agent profiles running: AR watcher, voucher scanner, customer outreach. Each has scoped tools and cannot access data outside its domain.
**Time:** ~3 hours

---

## Step 1: Understand Hermes Profile Architecture

Hermes supports multiple agent profiles via `config.yaml`. Each profile gets:
- Own personality (system prompt)
- Own skill set (which modules)
- Own MCP server access (tool scoping)
- Own cron jobs (what to run when)

Check if Hermes has runtime profile switching or requires separate gateway instances.

```bash
hermes profiles --help
hermes config get profiles
```

## Step 2: Verify Profile Configs Are Correct

The repo already has profile configs. Verify they match Hermes schema:

### AR Watcher (`config/profiles/ar_watcher.yaml`)
```yaml
name: ar_watcher
description: Monitors AR aging, generates collection letters, logs activity
personality: ar_watcher
skills:
  - icm_base
  - ar_collections
mcp_servers:
  - cognee
  - postgres
tools:
  deny:
    - browser_navigate
    - web_search
    - execute_code
    - google-workspace__gmail_send  # No direct email
```

### Voucher Scanner (`config/profiles/voucher_scanner.yaml`)
```yaml
name: voucher_scanner
description: Extracts voucher data, creates accounting entries, flags for review
personality: voucher_scanner
skills:
  - icm_base
  - voucher_processing
mcp_servers:
  - cognee
  - postgres
  - google-workspace  # Needs email for flag notifications
tools:
  deny:
    - browser_navigate
    - web_search
```

### Customer Outreach (`config/profiles/outreach_agent.yaml`)
```yaml
name: outreach_agent
description: Manages customer contact cadence, generates personalized outreach
personality: outreach
skills:
  - icm_base
  - customer_outreach
mcp_servers:
  - cognee
  - postgres
  - google-workspace  # Needs email for outreach delivery
tools:
  deny:
    - browser_navigate
    - web_search
```

## Step 3: Deploy Profiles to Hermes

```bash
# Link profile configs
cp config/profiles/ar_watcher.yaml ~/.hermes/profiles/
cp config/profiles/voucher_scanner.yaml ~/.hermes/profiles/  
cp config/profiles/outreach_agent.yaml ~/.hermes/profiles/

# Link personalities
cp config/profiles/ar_watcher.md ~/.hermes/personalities/bridge-and-bolt/
cp config/profiles/voucher_scanner.md ~/.hermes/personalities/bridge-and-bolt/
cp config/profiles/outreach.md ~/.hermes/personalities/bridge-and-bolt/

# Verify Hermes sees them
hermes profiles list
```

Expected output should show 4 profiles (default bridge-and-bolt + 3 named profiles).

## Step 4: Test Profile Scoping (AR Watcher)

Start AR watcher in isolated mode:

```bash
# Option A: Hermes supports profile flag
hermes gateway start --profile ar_watcher

# Option B: Separate config file
HERMES_CONFIG=~/.hermes/profiles/ar_watcher.yaml hermes gateway start
```

From Discord (or CLI, whichever the profile connects to):

```
1. "What tools do you have access to?"
   → Expected: AR-related tools only (cognee__memorize, cognee__query, postgres:query, postgres:execute)
   → NOT expected: google-workspace__*, browser__*

2. "Send an email to john@acme.example.com."
   → Expected: Agent says it doesn't have email access, or tool not found

3. "What vouchers are pending?"
   → Expected: ERROR or "I don't have access to the voucher system"
```

Checklist:
- [ ] AR watcher sees only PostgreSQL + Cognee tools
- [ ] AR watcher cannot access Google Workspace
- [ ] AR watcher cannot browse the web
- [ ] AR watcher can query AR tables and generate collection letters

## Step 5: Test Profile Scoping (Voucher Scanner)

Switch to voucher scanner profile:

```
1. "Email the review team about low-confidence extractions."
   → Expected: Has access to google-workspace__gmail_send (allowed in scoping)

2. "List all overdue invoices."
   → Expected: Can access ar_invoices (PostgreSQL is shared) but should defer to AR watcher
```

## Step 6: Test Cross-Profile Isolation

Critical test: can one profile's agent see another profile's session data?

```bash
# Start AR watcher, have a conversation
# Start voucher scanner, ask about AR watcher's conversation

"Can you see the conversation I had with the AR watcher about INV-2025-050?"
```

Expected: No. Each profile has isolated session context.

Checklist:
- [ ] AR watcher sessions are not visible to voucher scanner
- [ ] Voucher scanner sessions are not visible to outreach agent
- [ ] Cognee graph is shared (by design — knowledge graph is cross-profile)
- [ ] PostgreSQL data is shared (by design — single source of truth)

## Step 7: Write Profile Scoping Tests

Create `tests/test_profile_scoping.py`:

```python
"""Verify tool scoping per agent profile"""
import yaml
import pytest

def load_profile(name):
    with open(f"config/profiles/{name}.yaml") as f:
        return yaml.safe_load(f)

def test_ar_watcher_denies_email():
    """AR watcher should not have Gmail send access"""
    profile = load_profile("ar_watcher")
    deny = profile.get("tools", {}).get("deny", [])
    assert "google-workspace__gmail_send" in deny or "gmail_send" in str(deny)

def test_ar_watcher_denies_browser():
    """AR watcher should not browse the web"""
    profile = load_profile("ar_watcher")
    deny = profile.get("tools", {}).get("deny", [])
    assert any("browser" in d.lower() for d in deny)

def test_voucher_scanner_has_google():
    """Voucher scanner needs Google Workspace for review notifications"""
    profile = load_profile("voucher_scanner")
    mcp = profile.get("mcp_servers", [])
    assert "google-workspace" in mcp

def test_outreach_has_google():
    """Outreach agent needs Google Workspace for email delivery"""
    profile = load_profile("outreach_agent")
    mcp = profile.get("mcp_servers", [])
    assert "google-workspace" in mcp

def test_all_profiles_have_cognee():
    """All profiles must have Cognee graph access"""
    for name in ["ar_watcher", "voucher_scanner", "outreach_agent"]:
        profile = load_profile(name)
        mcp = profile.get("mcp_servers", [])
        assert "cognee" in mcp, f"{name} missing Cognee"

def test_all_profiles_have_postgres():
    """All profiles must have PostgreSQL access"""
    for name in ["ar_watcher", "voucher_scanner", "outreach_agent"]:
        profile = load_profile(name)
        mcp = profile.get("mcp_servers", [])
        assert "postgres" in mcp, f"{name} missing PostgreSQL"

def test_all_profiles_have_skills():
    """All profiles must have icm_base skill"""
    for name in ["ar_watcher", "voucher_scanner", "outreach_agent"]:
        profile = load_profile(name)
        skills = profile.get("skills", [])
        assert "icm_base" in skills, f"{name} missing icm_base"
```

Run:
```bash
pytest tests/test_profile_scoping.py -v
```

## Gate: Proceed to Phase 5 if...

- [ ] 3 profiles correctly deployed to Hermes
- [ ] AR watcher cannot access email or browser
- [ ] Voucher scanner has Google Workspace access
- [ ] Outreach agent has Google Workspace access
- [ ] Sessions are isolated between profiles
- [ ] Cognee graph is shared across profiles (knowledge is cross-profile)
- [ ] Profile scoping tests pass (7 tests)
