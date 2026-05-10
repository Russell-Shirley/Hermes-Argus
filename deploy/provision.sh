#!/bin/bash
# Hermes-Argus Provisioning Script v2
# Usage: ./deploy/provision.sh <org_slug> [--preset construction|dental|retail] [--modules a,b,c] [--cloud]
# Example: ./deploy/provision.sh acme-corp --preset construction
#          ./deploy/provision.sh metro-dental --preset dental --cloud

set -euo pipefail

ORG_SLUG="${1:?Usage: provision.sh <org_slug> [--preset type] [--modules a,b,c] [--cloud]}"
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
    # Extract modules from preset yaml using grep (no yq dependency)
    MODULES_FROM_PRESET=$(grep -A100 '^modules:' "$PRESET_FILE" | grep '^\s*- ' | sed 's/^\s*- //' | tr '\n' ',' | sed 's/,$//')
    if [[ -z "$MODULES" ]]; then
      MODULES="$MODULES_FROM_PRESET"
    fi
    echo " Loaded preset: $PRESET"
  else
    echo " Preset not found: $PRESET (expected at $PRESET_FILE)"
    exit 1
  fi
fi

# Default modules if nothing specified
MODULES="${MODULES:-icm_base}"

echo " Provisioning Hermes-Argus for $ORG_SLUG"
echo " Modules: $MODULES"
echo " Cloud deployment: $IS_CLOUD"
echo ""

# --- Validate prerequisites ---
command -v hermes >/dev/null 2>&1 || { echo " Hermes CLI not found"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo " Docker not found"; exit 1; }

# --- Directory setup ---
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ORG_DIR="$HERMES_HOME/orgs/$ORG_SLUG"
mkdir -p "$ORG_DIR"/{skills,config/profiles,cron,schema,templates,logs,data,review}

echo " Org directory: $ORG_DIR"

# --- Secure directory ---
chmod 700 "$ORG_DIR"

# --- Copy ICM modules (curated) ---
IFS=',' read -ra MODULE_ARRAY <<< "$MODULES"
for module in "${MODULE_ARRAY[@]}"; do
  MODULE_PATH="$PWD/modules/$module"
  if [[ -d "$MODULE_PATH" ]]; then
    cp -r "$MODULE_PATH" "$ORG_DIR/skills/$module"
    echo "   Module: $module"
  else
    echo "   Module not found: $module (skipping)"
  fi
done

# --- Copy and customize config ---
cp "$PWD/config/hermes.yaml" "$ORG_DIR/config/"
cp "$PWD/config/cron/jobs.json" "$ORG_DIR/cron/"
cp -r "$PWD/config/profiles/"* "$ORG_DIR/config/profiles/"
# Deploy default-profile SOUL.md (argus.md → SOUL.md at HERMES_HOME root)
cp "$PWD/config/profiles/argus.md" "$ORG_DIR/SOUL.md"
cp "$PWD/schema/business.sql" "$ORG_DIR/schema/"
cp -r "$PWD/templates"/* "$ORG_DIR/templates/"
echo " Configuration copied"

# Apply preset overrides
if [[ -n "$PRESET" ]] && [[ -f "$PRESET_FILE" ]]; then
  python3 deploy/apply_preset.py "$PRESET_FILE" "$ORG_DIR"
fi

# --- Cognee sidecar ---
if [[ ! -d "$ORG_DIR/cognee-server" ]]; then
  cp -r "$PWD/cognee-server" "$ORG_DIR/cognee-server"
  echo " Cognee server copied"
fi

# --- Google Workspace (optional - only if relevant modules) ---
if [[ -d "$PWD/google-tools" ]]; then
  if [[ "$MODULES" == *"customer_outreach"* ]] || [[ "$MODULES" == *"voucher_processing"* ]]; then
    cp -r "$PWD/google-tools" "$ORG_DIR/google-tools"
    echo " Google Workspace MCP copied"
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
DISCORD_ALLOWED_USERS=
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
SLACK_ALLOWED_USERS=
SLACK_HOME_CHANNEL=
POSTGRES_CONNECTION_STRING=postgresql://postgres:${DB_PASSWORD}@localhost:5432/argus_${ORG_SLUG}
HERMES_HOME=$ORG_DIR
ORG_SLUG=$ORG_SLUG
EOF
  chmod 600 "$ORG_DIR/.env"
  echo " .env created (fill in API keys)"
fi

# --- Preset-specific environment overrides ---
if [[ -n "$PRESET" ]]; then
  case "$PRESET" in
    dental)
      echo " Dental practice preset: enabling HIPAA compliance mode"
      echo "HIPAA_COMPLIANT=true" >> "$ORG_DIR/.env"
      echo "DATA_RETENTION_DAYS=2555" >> "$ORG_DIR/.env"
      ;;
    construction)
      echo " Construction preset: enabling progress billing and material tracking"
      ;;
    retail)
      echo " Retail preset: enabling inventory alerts and loyalty outreach"
      ;;
  esac
fi

# --- Cloud deployment extras ---
if [[ "$IS_CLOUD" == "true" ]]; then
  echo " Cloud deployment: generating cloud-specific config"
  cat >> "$ORG_DIR/config/hermes.yaml" <<EOF

# Cloud deployment overrides
terminal:
  backend: modal
  container_persistent: true
EOF
fi

# --- Database ---
echo ""
echo " Next steps:"
echo "   1. Edit $ORG_DIR/.env and set API keys"
echo "   2. Start Cognee: cd $ORG_DIR/cognee-server && docker compose up -d"
echo "   3. Run schema: psql \${POSTGRES_CONNECTION_STRING} -f $ORG_DIR/schema/business.sql"
echo "   4. Seed test data (optional): psql \${POSTGRES_CONNECTION_STRING} -f tests/fixtures/seed_test_data.sql (customize first!)"
echo "   5. Install skills: hermes skills install --dir $ORG_DIR/skills --profile $ORG_DIR"
echo "   6. Start gateway: HERMES_HOME=$ORG_DIR hermes gateway start"
echo "   7. Enable cron: hermes cron enable --all --profile $ORG_DIR"
echo ""
echo " $ORG_SLUG provisioned. Ready for onboarding."
