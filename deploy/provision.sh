#!/bin/bash
# Hermes-Argus Provisioning Script
# Usage: ./deploy/provision.sh <org_slug> [module_list]
# Example: ./deploy/provision.sh acme-corp ar_collections,voucher_processing,invoicing

set -euo pipefail

ORG_SLUG="${1:?Usage: provision.sh <org_slug> [modules]}"
MODULES="${2:-icm_base}"

echo "🚀 Provisioning Hermes-Argus for $ORG_SLUG"
echo "📦 Modules: $MODULES"
echo ""

# --- Validate prerequisites ---
command -v hermes >/dev/null 2>&1 || { echo "❌ Hermes CLI not found. Install: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found."; exit 1; }

# --- Directory setup ---
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ORG_DIR="$HERMES_HOME/orgs/$ORG_SLUG"
mkdir -p "$ORG_DIR"/{skills,config,cron,schema,templates,logs,data}

echo "📁 Org directory: $ORG_DIR"

# --- Copy ICM modules ---
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

# --- Copy config ---
cp "$PWD/config/hermes.yaml" "$ORG_DIR/config/"
cp "$PWD/config/cron/jobs.json" "$ORG_DIR/cron/"
cp "$PWD/schema/business.sql" "$ORG_DIR/schema/"
cp -r "$PWD/templates" "$ORG_DIR/templates"
echo "✅ Configuration copied"

# --- Cognee sidecar ---
if [[ ! -d "$ORG_DIR/cognee-server" ]]; then
  cp -r "$PWD/cognee-server" "$ORG_DIR/cognee-server"
  echo "✅ Cognee server copied"
fi

# --- Google Workspace (optional) ---
if [[ -d "$PWD/google-tools" ]]; then
  cp -r "$PWD/google-tools" "$ORG_DIR/google-tools"
  echo "✅ Google Workspace MCP copied"
fi

# --- Environment setup ---
if [[ ! -f "$ORG_DIR/.env" ]]; then
  cat > "$ORG_DIR/.env" <<EOF
# Hermes-Argus: $ORG_SLUG
DEEPSEEK_API_KEY=
DISCORD_BOT_TOKEN=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
POSTGRES_CONNECTION_STRING=postgresql://postgres:$(openssl rand -hex 16)@localhost:5432/argus_${ORG_SLUG}
HERMES_HOME=$ORG_DIR
EOF
  echo "✅ .env created (fill in API keys)"
fi

# --- Database ---
echo ""
echo "📊 Next steps:"
echo "   1. Edit $ORG_DIR/.env and set API keys"
echo "   2. Start Cognee: cd $ORG_DIR/cognee-server && docker compose up -d"
echo "   3. Run schema: psql \$POSTGRES_CONNECTION_STRING -f $ORG_DIR/schema/business.sql"
echo "   4. Link skills: hermes skills install --dir $ORG_DIR/skills"
echo "   5. Start gateway: HERMES_HOME=$ORG_DIR hermes gateway start"
echo ""
echo "🎉 $ORG_SLUG provisioned."
