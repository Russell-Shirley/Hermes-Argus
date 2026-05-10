-- Test customers
INSERT INTO customers (name, contact_name, contact_email, payment_terms, credit_limit)
VALUES
  ('Acme Construction', 'John Smith', 'john@acme.example.com', 'net60', 50000),
  ('Metro Dental', 'Sarah Jones', 'sarah@metrodental.example.com', 'net30', 25000),
  ('River City Plumbing', 'Mike Brown', 'mike@rivercity.example.com', 'net30', 15000)
ON CONFLICT DO NOTHING;

-- Test invoices (various aging buckets)
INSERT INTO ar_invoices (customer_name, invoice_number, invoice_date, due_date, amount, balance, status)
VALUES
  ('Acme Construction', 'INV-2026-001', '2026-01-15', '2026-02-14', 12000.00, 12000.00, 'open'),
  ('Acme Construction', 'INV-2026-002', '2025-12-01', '2025-12-31', 8500.00, 8500.00, 'open'),
  ('Acme Construction', 'INV-2025-050', '2025-09-15', '2025-10-15', 5000.00, 5000.00, 'open'),
  ('Metro Dental', 'INV-2026-003', '2026-02-01', '2026-03-03', 3500.00, 3500.00, 'open'),
  ('Metro Dental', 'INV-2026-004', '2026-04-01', '2026-04-15', 2200.00, 2200.00, 'open'),
  ('River City Plumbing', 'INV-2026-005', '2026-03-01', '2026-03-31', 1800.00, 1800.00, 'open'),
  ('River City Plumbing', 'INV-2026-006', '2026-05-01', '2026-05-31', 4200.00, 4200.00, 'open')
ON CONFLICT DO NOTHING;

-- Test voucher queue entries
INSERT INTO voucher_queue (filename, status, extracted_vendor, extracted_amount, confidence)
VALUES
  ('inv_acme_jan.pdf', 'pending', NULL, NULL, 0.0),
  ('receipt_metro_feb.pdf', 'pending', NULL, NULL, 0.0),
  ('inv_office_depot.pdf', 'needs_review', 'Office Depot', 245.50, 0.55)
ON CONFLICT DO NOTHING;

-- Test outreach schedule
INSERT INTO outreach_schedule (customer_name, last_contact, next_contact, cadence_days, contact_method)
VALUES
  ('Acme Construction', '2026-04-01', '2026-05-01', 30, 'email'),
  ('Metro Dental', '2026-04-15', '2026-05-10', 45, 'phone'),
  ('River City Plumbing', '2026-03-01', '2026-04-01', 30, 'email')
ON CONFLICT DO NOTHING;
