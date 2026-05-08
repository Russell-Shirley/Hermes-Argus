---
name: voucher_processing
version: 1.0.0
description: Invoice/voucher file ingestion, OCR data extraction, accounting entry creation
requires: [icm_base]
---

# Voucher Processing Module

## Database Tables
- `voucher_queue` — Files pending processing with extraction results
- `accounting_entries` — Posted accounting entries linked to vouchers

## Processing Pipeline

For each file in `voucher_queue` WHERE `status = 'pending'`:

1. Read the file. If it's a PDF or image, request OCR extraction.
2. Extract: vendor name, invoice number, date, amount, line items if available.
3. Determine confidence (0.0-1.0) for each extracted field.
4. If overall confidence >= 0.8:
   - INSERT into `accounting_entries` (vendor, amount, date, description)
   - UPDATE voucher_queue SET status = 'posted', accounting_entry_id = <new_id>
5. If overall confidence < 0.8:
   - UPDATE voucher_queue SET status = 'needs_review', flag all low-confidence fields
   - Notify review channel

## Common Vendors (learn per deployment)

When you encounter a new vendor, store it in Cognee with:
- Vendor name, typical invoice amounts, recurring cadence, GL account mappings

## Error Handling

- File unreadable → status 'failed', note error
- Duplicate invoice number → flag, do not post
- Amount mismatch with PO → flag for review
- Unknown vendor → extract what you can, flag for review
