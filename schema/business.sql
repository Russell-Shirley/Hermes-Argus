-- Hermes-Argus Business Schema
-- Deployed per-org on their PostgreSQL/Supabase instance

-- ============================================================
-- CUSTOMERS (must come first — referenced by ar_invoices, outreach)
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  contact_name TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  billing_address TEXT,
  payment_terms TEXT DEFAULT 'net30',
  credit_limit NUMERIC(12,2),
  status TEXT DEFAULT 'active',
    -- active, inactive, on_hold
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AR LEDGER
-- ============================================================

CREATE TABLE IF NOT EXISTS ar_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  customer_name TEXT NOT NULL,
  invoice_number TEXT NOT NULL,
  invoice_date DATE NOT NULL,
  due_date DATE NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  balance NUMERIC(12,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
    -- open, partial, paid, collections, disputed, written_off
  payment_terms TEXT DEFAULT 'net30',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ar_invoices_status ON ar_invoices(status);
CREATE INDEX idx_ar_invoices_due ON ar_invoices(due_date, status);
CREATE INDEX idx_ar_invoices_customer ON ar_invoices(customer_id);

CREATE OR REPLACE VIEW ar_invoices_aging AS
SELECT 
  id, customer_name, invoice_number, amount, balance, status,
  due_date,
  EXTRACT(DAY FROM NOW() - due_date)::INTEGER AS days_overdue,
  CASE 
    WHEN status = 'paid' THEN 'current'
    WHEN NOW() < due_date THEN 'current'
    WHEN NOW() >= due_date AND NOW() < due_date + INTERVAL '30 days' THEN '1-30'
    WHEN NOW() >= due_date + INTERVAL '30 days' AND NOW() < due_date + INTERVAL '60 days' THEN '31-60'
    WHEN NOW() >= due_date + INTERVAL '60 days' AND NOW() < due_date + INTERVAL '90 days' THEN '61-90'
    WHEN NOW() >= due_date + INTERVAL '90 days' AND NOW() < due_date + INTERVAL '120 days' THEN '91-120'
    WHEN NOW() >= due_date + INTERVAL '120 days' THEN '121+'
  END AS aging_bucket
FROM ar_invoices
WHERE status NOT IN ('paid', 'written_off');

-- ============================================================
-- COLLECTION ACTIVITY LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS collection_activity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES ar_invoices(id),
  action TEXT NOT NULL,
    -- letter_sent, call_attempted, call_completed, payment_received,
    -- payment_promise, dispute_filed, escalated
  letter_type TEXT,
    -- friendly, firm, final
  agent_note TEXT,
  amount_promised NUMERIC(12,2),
  promise_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collection_invoice ON collection_activity(invoice_id);

-- ============================================================
-- VOUCHER QUEUE
-- ============================================================

CREATE TABLE IF NOT EXISTS voucher_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT NOT NULL,
  file_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
    -- pending, processing, posted, needs_review, failed
  extracted_vendor TEXT,
  extracted_amount NUMERIC(12,2),
  extracted_date DATE,
  extracted_invoice_number TEXT,
  confidence FLOAT DEFAULT 0.0,
  accounting_entry_id TEXT,
  error_message TEXT,
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_voucher_status ON voucher_queue(status);

-- ============================================================
-- ACCOUNTING ENTRIES
-- ============================================================

CREATE TABLE IF NOT EXISTS accounting_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  voucher_id UUID REFERENCES voucher_queue(id),
  entry_type TEXT NOT NULL,
    -- ap_invoice, payment, journal
  vendor TEXT,
  description TEXT,
  amount NUMERIC(12,2),
  gl_account TEXT,
  entry_date DATE DEFAULT CURRENT_DATE,
  source TEXT DEFAULT 'hermes-argus',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CUSTOMER OUTREACH
-- ============================================================

CREATE TABLE IF NOT EXISTS outreach_schedule (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  customer_name TEXT NOT NULL,
  last_contact DATE,
  next_contact DATE,
  cadence_days INTEGER DEFAULT 30,
  contact_method TEXT DEFAULT 'email',
  status TEXT DEFAULT 'pending',
    -- pending, contacted, skipped, unsubscribed
  agent_note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outreach_next ON outreach_schedule(next_contact, status);

CREATE TABLE IF NOT EXISTS outreach_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schedule_id UUID REFERENCES outreach_schedule(id),
  customer_name TEXT NOT NULL,
  message TEXT,
  channel TEXT,
    -- email, phone, slack, sms
  response_received BOOLEAN DEFAULT false,
  response_summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outreach_log_customer ON outreach_log(customer_name);

-- ============================================================
-- EXTENSIBLE MODULES (deploy incrementally per-org)
-- ============================================================

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
  frequency TEXT,
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
  status TEXT DEFAULT 'pending',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- BACKUP OBSERVABILITY
-- ============================================================

CREATE TABLE IF NOT EXISTS backup_jobs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name    TEXT NOT NULL,
    -- 'restic+docker'
  job_name     TEXT NOT NULL,
    -- 'nightly-backup'
  target       TEXT,
    -- destination path, e.g. 'D:\hermes-backups'
  status       TEXT NOT NULL,
    -- 'success', 'failed', 'partial'
  size_bytes   NUMERIC,
  duration_sec INTEGER,
  error_message TEXT,
  started_at   TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_backup_jobs_status ON backup_jobs(status, created_at DESC);
