# Hermes-Argus Onboarding Checklist

## Pre-Deployment (Bridge and Bolt)

- [ ] ROI analysis completed (targets identified, scope agreed)
- [ ] Org type determined (construction, dental, retail, custom)
- [ ] Modules selected (what the client paid for)
- [ ] Messaging platform chosen (Discord or Slack)
- [ ] API keys ready (DeepSeek, Discord/Slack, Postgres)

## Provisioning (Technical)

- [ ] Server provisioned (on-prem hardware or cloud VM)
- [ ] Docker installed
- [ ] Hermes CLI installed
- [ ] Run: `./deploy/provision.sh <org_slug> --preset <type>`
- [ ] .env populated with API keys
- [ ] Cognee started: `docker compose up -d`
- [ ] Schema deployed: `psql ... -f schema/business.sql`
- [ ] Test data seeded (customized per client)
- [ ] Skills installed: `hermes skills install --dir skills/`
- [ ] Gateway started: `hermes gateway start`
- [ ] Cron enabled: `hermes cron enable --all`

## Validation (Before Client Handoff)

- [ ] Discord/Slack bot responds with correct personality
- [ ] "Remember X" triggers Cognee graph storage
- [ ] "What do you know about X" queries graph and returns facts
- [ ] AR check finds overdue invoices
- [ ] Collection letter drafted in review channel (not sent)
- [ ] Voucher processing extracts data correctly
- [ ] Approval flow works (approve sends, deny aborts)
- [ ] All existing tests pass

## Client Onboarding

- [ ] Client added to Discord/Slack allowlist
- [ ] Client trained on: asking the agent, reviewing drafts, approving/rejecting
- [ ] Client knows what the agent CAN and CANNOT do
- [ ] Review channel explained (where drafts appear before sending)
- [ ] Billing set up (monthly management fee)

## Day 1 Monitoring

- [ ] AR daily check ran on schedule
- [ ] Voucher watchdog processed correctly (if applicable)
- [ ] Outreach daily ran on schedule (if applicable)
- [ ] No unexpected tool calls or errors in logs
- [ ] Log review: no secrets leaked, no hallucinations in output

## Monthly Review

- [ ] Automation stats: tasks processed, letters drafted, time saved
- [ ] Error review: any flagged items needing process improvement
- [ ] Skill updates: any new workflows discovered worth adding
- [ ] Module upsell: any processes the client now wants automated
- [ ] Billing verified
