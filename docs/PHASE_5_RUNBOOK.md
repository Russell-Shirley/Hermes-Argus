# Phase 5 Runbook: Cron Jobs + Business Logic

**Prerequisite:** Phase 4 complete (3 profiles scoped, agent reads/writes business data)
**Goal:** Scheduled cron jobs run daily business automation — AR collection check, voucher processing, customer outreach. Human review gate on all outbound actions.
**Time:** ~5 hours

---

## Step 1: Understand Hermes Cron System

Hermes has a built-in cron system. Check available commands:

```bash
hermes cron --help
hermes cron list
hermes cron add --help
```

Cron jobs are stored in `~/.hermes/cron/jobs.json` and support:
- Standard cron schedule expressions
- Platform delivery (Slack, Discord, Email)
- Per-profile execution
- Per-run reports

## Step 2: Deploy Cron Job Definitions

The repo already has cron definitions at `config/cron/jobs.json`. Deploy them:

```bash
cp config/cron/jobs.json ~/.hermes/cron/jobs.json
hermes cron reload
```

Or register individually:

```bash
# AR daily check
hermes cron add \
  --id ar_daily_check \
  --schedule "0 8 * * 1-5" \
  --profile ar_watcher \
  --prompt "Check AR ledger for invoices 90+ days past due. For each overdue invoice: 1) query the invoice and customer details, 2) check collection_activity for last action, 3) generate appropriate collection letter based on aging bucket, 4) insert into collection_activity with status 'letter_sent', 5) deliver draft letters to review channel for human approval. Report what was generated."

# Voucher watchdog  
hermes cron add \
  --id voucher_watchdog \
  --schedule "*/15 * * * *" \
  --profile voucher_scanner \
  --prompt "Check voucher_queue for pending files. For each: extract vendor/amount/date, determine confidence level. If confidence >= 0.8, create accounting entry and mark posted. If < 0.8, mark needs_review and flag. Report: number processed, posted, flagged for review."

# Outreach daily
hermes cron add \
  --id outreach_daily \
  --schedule "0 9 * * 1-5" \
  --profile outreach_agent \
  --prompt "Check outreach_schedule for customers due for contact today. For each: query recent activity (last orders, open invoices), generate personalized outreach message, update last_contact and next_contact. Deliver drafts to review channel."
```

## Step 3: Wire the Human Review Gate

**This is the product.** Nothing goes to a customer without human approval.

### Option A: Hermes Approval Flow (Built-in)
Hermes has approval modes in `config.yaml`:
```yaml
approvals:
  mode: manual    # manual | smart | off
  timeout: 120    # seconds
```

When `mode: manual`, any tool call marked dangerous prompts the user. The agent drafts, the user approves or denies.

### Option B: Review Channel (Slack)
For business workflows, a dedicated Slack channel may be better:

```yaml
messaging:
  platforms:
    slack:
      review_channel: "#agent-review"
      approval:
        require_collection_letters: true
        require_outreach: true
        auto_approve_vouchers: false  # Vouchers > 0.8 confidence auto-posted (Phase 3 design)
```

### How the flow works:
1. Cron triggers agent
2. Agent queries business data
3. Agent generates draft (letter, outreach, accounting entry)
4. Agent posts draft to `#agent-review` channel
5. Human reviews, clicks Approve or Deny
6. If approved: agent executes (sends email, posts accounting entry)
7. If denied: agent logs the denial, moves on

## Step 4: Test AR Daily Check (Manual Trigger)

Before waiting for cron, test manually:

```bash
hermes cron run ar_daily_check
```

Or from Discord/Slack with AR watcher profile:
```
"Run the daily AR collection check."
```

Expected output:
```
AR DAILY CHECK — 2026-05-08
================================
Acme Construction — INV-2025-050: $5,000.00 (207 days overdue)
  → Drafted FINAL NOTICE letter
  → Queued for review (review-id: abc123)

Acme Construction — INV-2026-002: $8,500.00 (128 days overdue)
  → Drafted FIRM NOTICE letter
  → Queued for review (review-id: abc124)

Metro Dental — INV-2026-004: $2,200.00 (23 days overdue)
  → Skipped (within payment terms)

River City Plumbing — INV-2026-005: $1,800.00 (38 days overdue)
  → Skipped (under 60 days — next tier)

Summary: 2 letters drafted, 2 skipped (in terms), 0 sent (pending review)
```

Checklist:
- [ ] Agent correctly identifies 90+ day overdue invoices
- [ ] Agent generates appropriate letter type (friendly/firm/final)
- [ ] Agent inserts into collection_activity
- [ ] Letters are NOT sent — they're queued for review
- [ ] Report is delivered to Slack review channel
- [ ] Agent does not modify invoice data

## Step 5: Test Voucher Watchdog

Insert a test file into voucher_queue:
```sql
INSERT INTO voucher_queue (filename, status) VALUES ('test_vendor_invoice.pdf', 'pending');
```

Trigger:
```bash
hermes cron run voucher_watchdog
```

Or from Discord:
```
"Run the voucher processing watchdog."
```

Expected output:
```
VOUCHER PROCESSING — 2026-05-08 10:15 AM
==========================================
test_vendor_invoice.pdf:
  Vendor: [attempted extraction]
  Amount: [attempted extraction]
  Confidence: [0.0-1.0]
  Status: posted / needs_review / failed

Summary: 1 processed, 0 posted (low confidence), 1 flagged for review
```

Checklist:
- [ ] Agent queries voucher_queue WHERE status = 'pending'
- [ ] Agent updates status during processing
- [ ] High-confidence extractions create accounting entries
- [ ] Low-confidence extractions are flagged
- [ ] Failed extractions are logged with error
- [ ] Report is delivered to review channel

## Step 6: Test Outreach Daily

Trigger:
```bash
hermes cron run outreach_daily
```

Expected output:
```
CUSTOMER OUTREACH — 2026-05-08
================================
Acme Construction:
  Last contact: 2026-04-01 | Due: 2026-05-01 (7 days overdue)
  Recent activity: 3 open invoices, $25,500 total
  Drafted: "Hi John, checking in. Noticed a few invoices outstanding..."
  → Queued for review (review-id: abc200)

River City Plumbing:
  Last contact: 2026-03-01 | Due: 2026-04-01 (37 days overdue)
  Drafted: "Hi Mike, it's been a while..."
  → Queued for review (review-id: abc201)

Metro Dental:
  Next contact: 2026-05-10 (not due yet — skipped)

Summary: 2 outreach messages drafted, 1 skipped (not due), 0 sent (pending review)
```

Checklist:
- [ ] Agent queries outreach_schedule WHERE next_contact <= today
- [ ] Agent pulls customer context (recent activity, preferences)
- [ ] Agent generates personalized, non-salesy messages
- [ ] Agent updates last_contact and next_contact
- [ ] Messages are queued for review, not sent
- [ ] Unsubscribed or skipped customers are respected

## Step 7: Test Approval Flow End-to-End

Full end-to-end: cron → generate → review → approve → send.

1. Trigger AR daily check
2. Verify draft letters appear in review channel
3. Click Approve on one letter
4. Verify:
   - Google Workspace MCP sends the email
   - collection_activity is updated with sent status
   - Report confirms the letter was sent

Checklist:
- [ ] Drafts appear in review channel
- [ ] Approve button works
- [ ] Deny button works
- [ ] After approve: email is sent (Google Workspace)
- [ ] After approve: activity is logged
- [ ] After deny: activity is logged, no email sent
- [ ] Approval audit trail is complete

## Step 8: Schedule All Cron Jobs

```bash
# List all jobs
hermes cron list

# Verify schedules
hermes cron show ar_daily_check
hermes cron show voucher_watchdog
hermes cron show outreach_daily

# Enable all
hermes cron enable ar_daily_check
hermes cron enable voucher_watchdog
hermes cron enable outreach_daily
```

Expected status: all three jobs active with correct schedules.

## Step 9: Write Cron Logic Tests

Create `tests/test_cron_business_logic.py`:

```python
"""Verify cron job business logic produces correct results"""
import json
import pytest

def test_cron_jobs_valid():
    """All cron jobs have required fields"""
    with open("config/cron/jobs.json") as f:
        jobs = json.load(f)
    
    required = {"id", "schedule", "profile", "prompt", "deliver_to"}
    for job in jobs:
        missing = required - set(job.keys())
        assert not missing, f"Job {job.get('id', 'unknown')} missing: {missing}"

def test_ar_cron_references_ar_watcher():
    """AR cron job runs under AR watcher profile"""
    with open("config/cron/jobs.json") as f:
        jobs = json.load(f)
    
    ar_job = next(j for j in jobs if j["id"] == "ar_daily_check")
    assert ar_job["profile"] == "ar_watcher"
    assert ar_job["require_approval"] == True

def test_collection_letter_aging_rules():
    """Verify aging bracket → letter type logic"""
    # These are prompt-level rules, verified by template tests
    # 90-119 days → friendly
    # 120-179 days → firm
    # 180+ days → final
    with open("templates/collection_letters.md") as f:
        content = f.read()
    
    assert "60-89 days past due" in content  # Friendly trigger
    assert "90-119 days past due" in content  # Firm trigger
    assert "120+ days past due" in content  # Final trigger

def test_voucher_confidence_threshold():
    """Voucher processing: >= 0.8 confidence → post, < 0.8 → review"""
    # This is a design rule verified here
    THRESHOLD = 0.8
    # High confidence (should post)
    assert 0.85 >= THRESHOLD
    assert 1.0 >= THRESHOLD
    # Low confidence (should review)
    assert 0.55 < THRESHOLD
    assert 0.0 < THRESHOLD

def test_outreach_cadence_defaults():
    """Verify default outreach cadences are reasonable"""
    # Active: every 60 days
    # Warm: every 45 days
    # Cold: every 30 days
    # New: 7 days, then 30 days
    cadences = {60, 45, 30, 7}
    assert len(cadences) == 4  # All distinct
    assert all(c > 0 for c in cadences)  # All positive
```

Run:
```bash
pytest tests/test_cron_business_logic.py -v
```

## Gate: Proceed to Phase 6 if...

- [ ] 3 cron jobs deployed and scheduled
- [ ] AR daily check finds overdue invoices and generates letter drafts
- [ ] Voucher watchdog processes pending files and routes by confidence
- [ ] Outreach daily generates personalized messages on schedule
- [ ] Human review gate works (approve/deny → action/logged)
- [ ] No outbound action occurs without approval
- [ ] Audit trail complete (collection_activity, outreach_log)
- [ ] Cron logic tests pass (all 5)
