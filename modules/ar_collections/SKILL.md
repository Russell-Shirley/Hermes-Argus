---
name: ar_collections
version: 1.0.0
description: Accounts receivable aging monitoring, collection letter generation, payment tracking
requires: [icm_base]
---

# AR Collections Module

## Database Tables
- `ar_invoices` — Outstanding and paid invoices with aging
- `ar_invoices_aging` — View with days_overdue and aging_bucket columns
- `collection_activity` — Log of all collection actions taken
- `customers` — Customer contact info and payment terms

## Daily Workflow

1. Query `ar_invoices_aging` WHERE `aging_bucket IN ('91-120', '121+')` AND `status NOT IN ('disputed', 'paid')`
2. For each overdue invoice, check `collection_activity` for the most recent action
3. Generate the appropriate letter based on aging:
   - 90-119 days → Friendly reminder (see templates)
   - 120-179 days → Firm notice
   - 180+ days → Final notice
4. Insert a row into `collection_activity` with action = 'letter_sent'
5. Deliver draft letters to the review channel

## Letter Templates

See `templates/collection_letters/` for template markdown files.

## Aggregated Reporting

On Mondays, generate a summary:
```sql
SELECT customer_name, aging_bucket, COUNT(*), SUM(balance)
FROM ar_invoices_aging
GROUP BY customer_name, aging_bucket
ORDER BY SUM(balance) DESC;
```

## Red Flags to Flag for Human Review

- Single customer with >$10K in 120+ day aging
- Invoice in collections status for >30 days with no activity
- Customer disputing >3 invoices simultaneously
- Any invoice where balance exceeds customer credit_limit
