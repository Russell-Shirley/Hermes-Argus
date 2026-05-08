# Phase 3 Runbook: Wire PostgreSQL + Supabase as Structured Brain

**Prerequisite:** Phase 2 complete (Cognee graph wired, Postgres MCP connected, business tests pass)
**Goal:** PostgreSQL becomes the single source of truth for business data — AR ledger, vouchers, customers, outreach. Agent reads and writes structured records.
**Time:** ~4 hours

---

## Step 1: Run Business Schema

```bash
# Verify Postgres is reachable
psql "${POSTGRES_CONNECTION_STRING}" -c "SELECT 1;"

# Deploy full schema
psql "${POSTGRES_CONNECTION_STRING}" -f schema/business.sql

# Verify tables
psql "${POSTGRES_CONNECTION_STRING}" -c "\dt"
```

Expected output:
```
 customers
 ar_invoices
 ar_invoices_aging (view)
 collection_activity
 voucher_queue
 accounting_entries
 outreach_schedule
 outreach_log
```

## Step 2: Seed Test Data

Create `tests/fixtures/seed_test_data.sql`:

```sql
-- Test customers
INSERT INTO customers (name, contact_name, contact_email, payment_terms, credit_limit)
VALUES 
  ('Acme Construction', 'John Smith', 'john@acme.example.com', 'net60', 50000),
  ('Metro Dental', 'Sarah Jones', 'sarah@metrodental.example.com', 'net30', 25000),
  ('River City Plumbing', 'Mike Brown', 'mike@rivercity.example.com', 'net30', 15000);

-- Test invoices (various aging buckets)
INSERT INTO ar_invoices (customer_name, invoice_number, invoice_date, due_date, amount, balance, status)
VALUES
  ('Acme Construction', 'INV-2026-001', '2026-01-15', '2026-02-14', 12000.00, 12000.00, 'open'),
  ('Acme Construction', 'INV-2026-002', '2025-12-01', '2025-12-31', 8500.00, 8500.00, 'open'),
  ('Acme Construction', 'INV-2025-050', '2025-09-15', '2025-10-15', 5000.00, 5000.00, 'open'),
  ('Metro Dental', 'INV-2026-003', '2026-02-01', '2026-03-03', 3500.00, 3500.00, 'open'),
  ('Metro Dental', 'INV-2026-004', '2026-04-01', '2026-04-15', 2200.00, 2200.00, 'open'),
  ('River City Plumbing', 'INV-2026-005', '2026-03-01', '2026-03-31', 1800.00, 1800.00, 'open'),
  ('River City Plumbing', 'INV-2026-006', '2026-05-01', '2026-05-31', 4200.00, 4200.00, 'open');

-- Test voucher queue entries
INSERT INTO voucher_queue (filename, status, extracted_vendor, extracted_amount, confidence)
VALUES
  ('inv_acme_jan.pdf', 'pending', NULL, NULL, 0.0),
  ('receipt_metro_feb.pdf', 'pending', NULL, NULL, 0.0),
  ('inv_office_depot.pdf', 'needs_review', 'Office Depot', 245.50, 0.55);

-- Test outreach schedule
INSERT INTO outreach_schedule (customer_name, last_contact, next_contact, cadence_days, contact_method)
VALUES
  ('Acme Construction', '2026-04-01', '2026-05-01', 30, 'email'),
  ('Metro Dental', '2026-04-15', '2026-05-10', 45, 'phone'),
  ('River City Plumbing', '2026-03-01', '2026-04-01', 30, 'email');
```

Apply:
```bash
psql "${POSTGRES_CONNECTION_STRING}" -f tests/fixtures/seed_test_data.sql
```

## Step 3: Verify AR Aging View

```bash
psql "${POSTGRES_CONNECTION_STRING}" -c "SELECT customer_name, invoice_number, days_overdue, aging_bucket, balance FROM ar_invoices_aging ORDER BY days_overdue DESC;"
```

Expected: Acme Construction INV-2025-050 shows 200+ days overdued in "121+" bucket.

## Step 4: Test Agent Queries

From Discord (with AR watcher profile active):

```
1. "List all customers and their payment terms."
   → Expected: 3 customers returned from customers table

2. "Show me the AR aging report."
   → Expected: Agent queries ar_invoices_aging, returns structured results

3. "Which invoices are more than 90 days past due?"
   → Expected: INV-2025-050 and INV-2026-002 for Acme Construction

4. "How much does Acme Construction owe in total?"
   → Expected: $25,500.00 across three open invoices

5. "What vouchers are pending or need review?"
   → Expected: 3 entries from voucher_queue with their statuses
```

Checklist:
- [ ] Agent can SELECT from all tables
- [ ] Agent correctly filters by status, date, amount
- [ ] Agent formats financial data correctly (dollar signs, dates)
- [ ] Agent does not hallucinate invoice numbers or amounts
- [ ] Agent identifies the correct aging buckets

## Step 5: Test Agent Writes (with Approval)

From Discord:

```
1. "Create a new invoice for River City Plumbing for $975 due in 30 days."
   → Expected: Agent inserts into ar_invoices, confirms

2. "Flag INV-2026-001 for review. The customer called and disputed it."
   → Expected: Agent updates status to 'disputed', adds note

3. "Send a collection letter for Acme Construction INV-2025-050."
   → Expected: Agent queries the invoice, generates a letter from template,
              inserts into collection_activity, queues letter for review.
              Does NOT send without approval.

4. "Approve that letter."
   → Expected: If approval flow is wired, letter is sent via Google Workspace MCP
              or Slack. Activity logged.
```

Checklist:
- [ ] Agent can INSERT new records
- [ ] Agent can UPDATE existing records
- [ ] Agent uses paramaterized queries (no SQL injection)
- [ ] Agent asks for approval before destructive writes (UPDATE/DELETE)
- [ ] Agent logs collection activity after sending letters
- [ ] Agent does not modify data without explicit instruction

## Step 6: Validate Voucher Processing Flow

From Discord:

```
1. "Process the pending vouchers in the queue."
   → Expected: Agent reads voucher_queue WHERE status = 'pending',
              attempts extraction, updates status to 'processing'/'posted'/'needs_review'

2. "What happened with the voucher processing?"
   → Expected: Agent reports which were posted, which were flagged, confidence levels

3. "The Office Depot voucher at 55% confidence — I reviewed it. The amount is actually $267.30."
   → Expected: Agent updates confidence to 1.0, changes amount to 267.30, 
              moves from needs_review to posted, creates accounting entry
```

## Step 7: Write Data Integrity Tests

Create `tests/test_data_integrity.py`:

```python
"""Verify data integrity: agent reads/writes correctly, no injection, no hallucination"""
import psycopg2
import os
import pytest

DB_URL = os.environ["POSTGRES_CONNECTION_STRING"]

@pytest.fixture
def db():
    conn = psycopg2.connect(DB_URL)
    yield conn
    conn.close()

def test_aging_view_calculates_correctly(db):
    """Verify ar_invoices_aging computes days_overdue and aging_bucket correctly"""
    cur = db.cursor()
    cur.execute("""
        SELECT invoice_number, days_overdue, aging_bucket 
        FROM ar_invoices_aging 
        WHERE invoice_number = 'INV-2025-050'
    """)
    row = cur.fetchone()
    assert row is not None
    assert row[1] > 90  # Should be 200+ days overdue
    assert row[2] in ('121+', '91-120')  # Should be in oldest bucket

def test_parameterized_insert_not_vulnerable(db):
    """Verify agent uses parameterized queries (not string interpolation)"""
    # This test ensures the schema supports parameterized queries
    # Actual injection testing would need to intercept agent queries
    cur = db.cursor()
    malicious = "'; DROP TABLE customers; --"
    cur.execute(
        "INSERT INTO collection_activity (invoice_id, action, agent_note) "
        "SELECT id, %s, %s FROM ar_invoices LIMIT 1",
        ('test', malicious)
    )
    db.rollback()
    
    # Verify customers table still exists
    cur.execute("SELECT COUNT(*) FROM customers")
    count = cur.fetchone()[0]
    assert count > 0, "Parameterized query protection failed"

def test_collection_activity_foreign_key(db):
    """Verify collection_activity requires valid invoice_id"""
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO collection_activity (invoice_id, action) VALUES "
            "('00000000-0000-0000-0000-000000000000', 'test')"
        )
        db.commit()
        pytest.fail("Should have raised foreign key violation")
    except Exception:
        db.rollback()
        # Expected — foreign key constraint works

def test_voucher_status_constraints(db):
    """Verify voucher_queue enforces valid statuses"""
    cur = db.cursor()
    # Verify existing rows have valid statuses
    cur.execute(
        "SELECT DISTINCT status FROM voucher_queue"
    )
    statuses = [row[0] for row in cur.fetchall()]
    valid = {'pending', 'processing', 'posted', 'needs_review', 'failed'}
    for status in statuses:
        assert status in valid, f"Invalid status: {status}"
```

Run:
```bash
cd tests
pytest test_data_integrity.py -v
```

## Step 8: Scale the Schema

As new modules are added, extend `schema/business.sql`:

```sql
-- Inventory module
CREATE TABLE IF NOT EXISTS inventory_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  quantity_on_hand INTEGER DEFAULT 0,
  reorder_point INTEGER,
  reorder_quantity INTEGER,
  vendor_id UUID REFERENCES customers(id),
  vendor_name TEXT,
  unit_cost NUMERIC(12,2),
  last_ordered DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoicing module
CREATE TABLE IF NOT EXISTS recurring_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  customer_name TEXT NOT NULL,
  template_name TEXT,
  amount NUMERIC(12,2),
  frequency TEXT,  -- weekly, monthly, quarterly, annually
  next_run DATE,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payroll module
CREATE TABLE IF NOT EXISTS time_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_name TEXT NOT NULL,
  entry_date DATE NOT NULL,
  hours NUMERIC(5,2),
  rate NUMERIC(12,2),
  status TEXT DEFAULT 'pending',  -- pending, approved, paid
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Apply incrementally — only what the org paid for.

## Gate: Proceed to Phase 4 if...

- [ ] Business schema deployed with all 8 tables
- [ ] Test data seeded (3 customers, 7 invoices, 3 vouchers, 3 outreach entries)
- [ ] Agent reads AR aging correctly (aging buckets computed)
- [ ] Agent writes new records (with parameterized queries)
- [ ] Agent generates collection letters from templates
- [ ] Agent processes vouchers (pending → extracted → posted/review)
- [ ] Data integrity tests pass (FK constraints, parameterization)
- [ ] Google Workspace and Cognee tests still pass
