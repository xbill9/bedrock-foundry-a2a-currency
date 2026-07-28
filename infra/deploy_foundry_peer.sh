#!/bin/bash
# Deploy the Azure half of the loop:
#   1. sync coordinator/ + mcp_server/ into the foundry_agent bundle
#   2. azd provision + deploy the Foundry hosted agent (responses protocol)
#   3. PATCH the agent to publish its card and enable incoming A2A
#
# Requires `az login` and `azd auth login`, plus Foundry Project Manager on the
# account for provisioning (see infra/README.md). Prints the A2A endpoint to
# feed back into the AgentCore runtime configuration.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_DIR="$REPO_ROOT/foundry_agent"
AGENT_NAME="${FOUNDRY_AGENT_NAME:-currency-a2a-agent}"
AZD_ENV="${AZD_ENV_NAME:-bedrock-foundry-a2a-currency-dev}"

echo "=== 1/3 sync packages into the agent bundle ==="
"$REPO_ROOT/infra/sync_app.sh"

echo "=== 2/3 azd provision + deploy ==="
cd "$AGENT_DIR"
azd env select "$AZD_ENV" 2>/dev/null || azd env new "$AZD_ENV"
azd env set CURRENCY_RATE_PROVIDER "${CURRENCY_RATE_PROVIDER:-frankfurter}"
azd provision --no-prompt
azd deploy --no-prompt

PROJECT_ENDPOINT="${FOUNDRY_PROJECT_ENDPOINT:-$(azd env get-value FOUNDRY_PROJECT_ENDPOINT 2>/dev/null || true)}"
if [[ -z "$PROJECT_ENDPOINT" ]]; then
  echo "Could not read FOUNDRY_PROJECT_ENDPOINT from the azd environment." >&2
  echo "Export it (https://<account>.services.ai.azure.com/api/projects/<project>) and rerun." >&2
  exit 2
fi

echo "=== 3/3 enable incoming A2A ==="
cd "$REPO_ROOT"
FOUNDRY_PROJECT_ENDPOINT="$PROJECT_ENDPOINT" FOUNDRY_AGENT_NAME="$AGENT_NAME" \
  python3 infra/enable_foundry_a2a.py

echo "=== Done. Grant the coordinator's service principal the Foundry Agent"
echo "    Consumer role on this project, then run infra/configure_azure_secret.sh. ==="
