# Phase 6 Runbook: Per-Org Deployment

**Prerequisite:** Phase 5 complete (cron running, business logic verified, approval flow working)
**Goal:** A single script provisions a complete Hermes-Argus appliance for a new SMB client in under 30 minutes.
**Time:** ~3 hours

---

## Step 1: Review the Provisioning Script

The repo has `deploy/provision.sh`. Review and harden:

```bash
cat deploy/provision.sh
```

Key design decisions in the script:
- Each org gets its own `~/.hermes/orgs/<slug>/` directory
- Modules are curated — only the ones paid for are copied
- Database schema is applied from `schema/business.sql`
- `.env` is generated with a random Postgres password
- Cognee is copied as a sidecar (Docker container per org)

## Step 2: Create Org-Specific Config Templates

Not every business is a construction company with net60 terms. Templates must be parameterized.

Create `deploy/templates/` with org-type presets:

### Construction Company Preset (`deploy/templates/construction.yaml`)
```yaml
org_type: construction
payment_terms: net60
modules:
  - icm_base
  - ar_collections
  - voucher_processing
  - inventory          # Material tracking
  - invoicing          # Progress billing
profiles:
  - ar_watcher
  - voucher_scanner
  - inventory_manager
review_rules:
  collection_letter_auto_approve: false   # Never auto-approve financial letters
  voucher_auto_post_threshold: 0.85       # Higher threshold for construction (complex invoices)
  outreach_auto_send: false               # Always review before contacting customer
```

### Dental Practice Preset (`deploy/templates/dental.yaml`)
```yaml
org_type: dental_practice
payment_terms: net30
modules:
  - icm_base
  - ar_collections     # Patient billing
  - customer_outreach  # Patient recall
  - invoicing          # Insurance + patient billing
profiles:
  - ar_watcher
  - outreach_agent
review_rules:
  collection_letter_auto_approve: false
  voucher_auto_post_threshold: 0.80
  outreach_auto_approve: false
  hippa_compliant: true  # Additional data handling rules
```

### Retail Business Preset (`deploy/templates/retail.yaml`)
```yaml
org_type: retail
payment_terms: net30
modules:
  - icm_base
  - ar_collections
  - voucher_processing
  - inventory            # Stock management
  - customer_outreach    # Loyalty/retention
  - invoicing
profiles:
  - ar_watcher
  - voucher_scanner
  - inventory_manager
  - outreach_agent
review_rules:
  collection_letter_auto_approve: false
  voucher_auto_post_threshold: 0.75      # Retail invoices are simpler, lower threshold ok
  outreach_auto_approve: false
  low_stock_alert_auto: true             # Inventory alerts can auto-fire
```

## Step 3: Enhance the Provisioning Script

Add features to `deploy/provision.sh`:

```bash
#!/bin/bash
# Hermes-Argus Provisioning Script v2
# Usage: ./deploy/provision.sh <org_slug> [--preset construction|dental|retail] [--modules a,b,c] [--cloud]
# Example: ./deploy/provision.sh acme-corp --preset construction
#          ./deploy/provision.sh metro-dental --preset dental --cloud

set -euo pipefail

ORG_SLUG="${1:?Usage: provision.sh <org_slug> [--preset type] [--modules a,b,c]}"
shift

PRESET=""
MODULES=""
IS_CLOUD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset) PRESET="$2"; shift 2 ;;
    --modules) MODULES="$2"; shift 2 ;;
    --cloud) IS_CLOUD=true; shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# Load preset if specified
if [[ -n "$PRESET" ]]; then
  PRESET_FILE="deploy/templates/${PRESET}.yaml"
  if [[ -f "$PRESET_FILE" ]]; then
    MODULES=$(yq '.modules | join(",")' "$PRESET_FILE")
    echo "📋 Loaded preset: $PRESET ($MODULES)"
  else
    echo "❌ Preset not found: $PRESET"
    exit 1
  fi
fi

# Default modules if nothing specified
MODULES="${MODULES:-icm_base}"

echo "🚀 Provisioning Hermes-Argus for $ORG_SLUG"
echo "📦 Modules: $MODULES"
echo "☁️  Cloud deployment: $IS_CLOUD"
echo ""

# --- Validate prerequisites ---
command -v hermes >/dev/null 2>&1 || { echo "❌ Hermes CLI not found"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }

# --- Directory setup ---
ORG_DIR="${HERMES_HOME:-$HOME/.hermes}/orgs/${ORG_SLUG}"
mkdir -p "$ORG_DIR"/{skills,config,cron,schema,templates,logs,data,review}

echo "📁 Org directory: $ORG_DIR"

# --- Secure directory ---
chmod 700 "$ORG_DIR"

# --- Copy ICM modules (curated) ---
IFS=',' read -ra MODULE_ARRAY <<< "$MODULES"
for module in "${MODULE_ARRAY[@]}"; do
  MODULE_PATH="$PWD/modules/$module"
  if [[ -d "$MODULE_PATH" ]]; then
    cp -r "$MODULE_PATH" "$ORG_DIR/skills/$module"
    echo "  ✅ Module: $module"
  else
    echo "  ⚠️  Module not found: $module (skipping)"
  fi
done

# --- Copy and customize config ---
cp "$PWD/config/hermes.yaml" "$ORG_DIR/config/"
cp "$PWD/config/cron/jobs.json" "$ORG_DIR/cron/"
mkdir -p "$ORG_DIR/config/profiles"
cp -r "$PWD/config/profiles/"* "$ORG_DIR/config/profiles/"

# Apply preset overrides
if [[ -n "$PRESET" ]]; then
  # Customize payment terms, review rules, module-specific config
  python3 deploy/apply_preset.py "$PRESET_FILE" "$ORG_DIR"
fi

# --- Copy schema ---
cp "$PWD/schema/business.sql" "$ORG_DIR/schema/"

# --- Copy templates ---
cp -r "$PWD/templates"/* "$ORG_DIR/templates/"

# --- Cognee sidecar ---
COGNEE_DIR="$ORG_DIR/cognee-server"
if [[ ! -d "$COGNEE_DIR" ]]; then
  cp -r "$PWD/cognee-server" "$COGNEE_DIR"
  echo "✅ Cognee server copied"
fi

# --- Google Workspace (optional) ---
if [[ -d "$PWD/google-tools" ]]; then
  # Only copy if org paid for email integration
  if [[ "$MODULES" == *"customer_outreach"* ]] || [[ "$MODULES" == *"voucher_processing"* ]]; then
    cp -r "$PWD/google-tools" "$ORG_DIR/google-tools"
    echo "✅ Google Workspace MCP copied"
  fi
fi

# --- Environment setup ---
if [[ ! -f "$ORG_DIR/.env" ]]; then
  DB_PASSWORD=$(openssl rand -hex 16)
  cat > "$ORG_DIR/.env" <<EOF
# Hermes-Argus: $ORG_SLUG
# Generated: $(date -Iseconds)
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
DISCORD_BOT_TOKEN=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
POSTGRES_CONNECTION_STRING=postgresql://postgres:${DB_PASSWORD}@localhost:5432/argus_${ORG_SLUG}
HERMES_HOME=$ORG_DIR
ORG_SLUG=$ORG_SLUG
EOF
  chmod 600 "$ORG_DIR/.env"
  echo "✅ .env created (fill in API keys)"
fi

# --- Preset-specific setup ---
if [[ -n "$PRESET" ]]; then
  case "$PRESET" in
    dental)
      echo "🦷 Dental practice preset: enabling HIPAA compliance mode"
      echo "HIPAA_COMPLIANT=true" >> "$ORG_DIR/.env"
      echo "DATA_RETENTION_DAYS=2555" >> "$ORG_DIR/.env"  # 7 years
      ;;
    construction)
      echo "🏗️  Construction preset: enabling progress billing and material tracking"
      ;;
    retail)
      echo "🏪 Retail preset: enabling inventory alerts and loyalty outreach"
      ;;
  esac
fi

# --- Cloud deployment extras ---
if [[ "$IS_CLOUD" == "true" ]]; then
  echo "☁️  Cloud deployment: generating cloud-specific config"
  cat >> "$ORG_DIR/config/hermes.yaml" <<EOF

# Cloud deployment overrides
terminal:
  backend: modal  # or daytona, vercel_sandbox
  container_persistent: true
EOF
fi

# --- Database ---
echo ""
echo "📊 Next steps:"
echo "   1. Edit $ORG_DIR/.env and set API keys"
echo "   2. Start Cognee: cd $ORG_DIR/cognee-server && docker compose up -d"
echo "   3. Run schema: psql \${POSTGRES_CONNECTION_STRING} -f $ORG_DIR/schema/business.sql"
echo "   4. Seed test data (optional): psql \${POSTGRES_CONNECTION_STRING} -f tests/fixtures/seed_test_data.sql (customize first!)"
echo "   5. Install skills: hermes skills install --dir $ORG_DIR/skills --profile $ORG_DIR"
echo "   6. Start gateway: HERMES_HOME=$ORG_DIR hermes gateway start"
echo "   7. Enable cron: hermes cron enable --all --profile $ORG_DIR"
echo ""
echo "🎉 $ORG_SLUG provisioned. Ready for onboarding."
```

## Step 4: Create the Preset Applicator

Create `deploy/apply_preset.py`:

```python
#!/usr/bin/env python3
"""Apply org-type preset overrides to a provisioned Hermes-Argus instance."""
import yaml
import sys
import os
from pathlib import Path

def apply_preset(preset_file: str, org_dir: str):
    with open(preset_file) as f:
        preset = yaml.safe_load(f)
    
    org_type = preset.get("org_type", "unknown")
    review_rules = preset.get("review_rules", {})
    
    # Update Hermes config with org-specific settings
    config_path = Path(org_dir) / "config" / "hermes.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Apply review rules
        if "approvals" not in config:
            config["approvals"] = {}
        config["approvals"]["mode"] = "manual"  # Always manual for business
        
        # Apply voucher threshold
        if "voucher_auto_post_threshold" in review_rules:
            threshold = review_rules["voucher_auto_post_threshold"]
            # Store as env var so the agent prompt can reference it
            env_path = Path(org_dir) / ".env"
            with open(env_path, "a") as env_f:
                env_f.write(f"\nVOUCHER_CONFIDENCE_THRESHOLD={threshold}")
        
        # Apply HIPAA flag
        if review_rules.get("hippa_compliant"):
            config["security"] = config.get("security", {})
            config["security"]["data_retention_days"] = 2555  # 7 years
            config["security"]["encrypt_at_rest"] = True
        
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
    
    print(f"✅ Applied {org_type} preset overrides to {org_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: apply_preset.py <preset_file> <org_dir>")
        sys.exit(1)
    apply_preset(sys.argv[1], sys.argv[2])
```

## Step 5: Test a Clean Provision

```bash
# Test construction company
./deploy/provision.sh test-construction --preset construction

# Verify output
tree ~/.hermes/orgs/test-construction/
ls -la ~/.hermes/orgs/test-construction/.env  # Should be 600

# Check config was customized
grep "VOUCHER_CONFIDENCE_THRESHOLD" ~/.hermes/orgs/test-construction/.env
```

Expected: directory created, modules copied, config customized, `.env` permissions 600.

## Step 6: Test a Dental Practice Provision

```bash
./deploy/provision.sh test-dental --preset dental

# Verify HIPAA flags
grep "HIPAA_COMPLIANT" ~/.hermes/orgs/test-dental/.env
grep "DATA_RETENTION_DAYS" ~/.hermes/orgs/test-dental/.env
```

Expected: HIPAA flag set to true, data retention set to 2555 days (7 years).

## Step 7: Test Full End-to-End Deploy + Smoke Test

```bash
# Provision
./deploy/provision.sh smoke-test-corp --preset construction

# Set up (simulate what the deploy script tells the operator to do)
cd ~/.hermes/orgs/smoke-test-corp
# Start Cognee
cd cognee-server && docker compose up -d && cd ..
# Deploy schema
psql "${POSTGRES_CONNECTION_STRING}" -f schema/business.sql
# Seed minimal test data
psql "${POSTGRES_CONNECTION_STRING}" <<SQL
INSERT INTO customers (name, contact_name, payment_terms)
VALUES ('Demo Corp', 'Test Contact', 'net60');
SQL
# Start gateway
HERMES_HOME="$(pwd)" hermes gateway start &
sleep 5
# Run AR check
hermes cron run ar_daily_check
```

Checklist:
- [ ] Provision completes in under 2 minutes
- [ ] Cognee starts successfully
- [ ] Schema deploys
- [ ] Gateway starts
- [ ] AR cron runs and produces output

## Step 8: Write Deployment Tests

Create `tests/test_deployment.py`:

```python
"""Verify deployment scripts produce correct output"""
import subprocess
import yaml
import pytest
from pathlib import Path

PROVISION_SCRIPT = Path("deploy/provision.sh")

def test_provision_script_exists():
    assert PROVISION_SCRIPT.exists()
    assert PROVISION_SCRIPT.stat().st_mode & 0o100  # Executable

def test_construction_preset_valid_yaml():
    with open("deploy/templates/construction.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "construction"
    assert "ar_collections" in preset["modules"]
    assert "voucher_processing" in preset["modules"]

def test_dental_preset_valid_yaml():
    with open("deploy/templates/dental.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "dental_practice"
    assert preset["review_rules"]["hippa_compliant"] == True

def test_retail_preset_valid_yaml():
    with open("deploy/templates/retail.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "retail"
    assert "inventory" in preset["modules"]

def test_all_presets_inherit_icm_base():
    for preset_name in ["construction", "dental", "retail"]:
        with open(f"deploy/templates/{preset_name}.yaml") as f:
            preset = yaml.safe_load(f)
        assert "icm_base" in preset["modules"], f"{preset_name} missing icm_base"

def test_all_presets_have_review_rules():
    for preset_name in ["construction", "dental", "retail"]:
        with open(f"deploy/templates/{preset_name}.yaml") as f:
            preset = yaml.safe_load(f)
        rules = preset.get("review_rules", {})
        assert "collection_letter_auto_approve" in rules, f"{preset_name} missing review rule"
        assert rules["collection_letter_auto_approve"] == False  # Must always be false
```

Run:
```bash
pytest tests/test_deployment.py -v
```

## Step 9: Create Onboarding Checklist for Clients

Create `deploy/ONBOARDING.md`:

```markdown
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
- [ ] Skills installed: `hermes skills install --dir skills/`
- [ ] Gateway started: `hermes gateway start`
- [ ] Cron enabled: `hermes cron enable --all`

## Validation (Before Client Handoff)
- [ ] Discord/Slack bot responds
- [ ] "Remember X" works (graph memory)
- [ ] "What do you know about X" works
- [ ] AR check finds test data
- [ ] Collection letter drafted (not sent)
- [ ] Voucher processing works
- [ ] Approval flow works (approve/deny)
- [ ] All existing tests pass

## Client Onboarding
- [ ] Client added to Discord/Slack allowlist
- [ ] Client trained on: asking the agent, approving/rejecting actions
- [ ] Client knows what the agent CAN and CANNOT do
- [ ] Review channel explained (where drafts appear)
- [ ] Billing set up (monthly management fee)

## Day 1 Monitoring
- [ ] AR daily check ran successfully
- [ ] Voucher watchdog processed correctly
- [ ] Outreach daily ran (if applicable)
- [ ] No unexpected tool calls or errors
- [ ] Log review: no secrets leaked, no hallucinations
```

## Gate: Project Complete if...

- [ ] Provision script deploys a complete appliance in < 30 minutes
- [ ] 3 org-type presets (construction, dental, retail) all provision correctly
- [ ] Provision → config → Cognee → schema → gateway → cron — full pipeline works
- [ ] Onboarding checklist complete and client-ready
- [ ] Deployment tests pass (6 tests)
- [ ] All previous phase tests still pass (Phases 0-5)
- [ ] Demo: can provision a construction company and run an AR check in under 30 minutes
