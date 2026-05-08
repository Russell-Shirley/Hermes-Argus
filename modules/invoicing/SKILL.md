---
name: invoicing
version: 1.0.0
description: Bill generation, recurring invoice scheduling, invoice delivery
requires: [icm_base]
---

# Invoicing Module

## Capabilities

- Generate invoices from completed work orders or contracts
- Schedule recurring invoices on configurable cycles
- Deliver invoices via email (Google Workspace MCP) or customer portal
- Track invoice status: draft, sent, viewed, paid, overdue

## Integration Points

- Pull billing data from PostgreSQL
- Store invoice templates as skills
- Use Cognee to remember customer-specific billing preferences
