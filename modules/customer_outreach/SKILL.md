---
name: customer_outreach
version: 1.0.0
description: Customer contact scheduling, personalized outreach generation, engagement tracking
requires: [icm_base]
---

# Customer Outreach Module

## Database Tables
- `outreach_schedule` — Who to contact and when
- `outreach_log` — Record of all outreach messages and responses
- `customers` — Contact info and status

## Daily Workflow

1. Query `outreach_schedule` WHERE `next_contact <= CURRENT_DATE` AND `status = 'pending'`
2. For each customer due for contact:
   - Check recent activity: last order date, open invoices, support tickets
   - Query Cognee for notable facts about this customer (preferences, history)
   - Generate a personalized, non-salesy check-in message
   - INSERT into `outreach_log` with the draft message
   - UPDATE `outreach_schedule.last_contact = NOW()`, `next_contact = NOW() + cadence_days`
3. Deliver drafts to review channel

## Tone Guidelines

- Reference something specific and recent ("I saw you ordered X last month...")
- Ask, don't pitch. "How's it working out?" not "Want to buy more?"
- Keep it short. 2-3 sentences max.
- Never mention financials unless relevant to the relationship.

## Cadence Defaults

- Active customers (ordered in last 30 days): every 60 days
- Warm customers (ordered in last 90 days): every 45 days
- Cold customers (>90 days no order): every 30 days
- New customers (first order <90 days): 7 days, 30 days, then standard

## Red Flags

- Customer who hasn't responded to 3+ outreaches → flag for review
- Customer who explicitly asked not to be contacted → mark unsubscribed
