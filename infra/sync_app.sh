#!/bin/bash
# Copy the framework-independent packages into each deployable bundle so both
# uploads are self-contained (neither runtime can import from outside its own
# directory). Run before `agentcore deploy` and before `azd deploy`. The copies
# are build artifacts: edit the repo-root packages, never the copies.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sync_into() {
  local dest="$1"
  shift
  for pkg in "$@"; do
    rm -rf "$dest/$pkg"
    rsync -a --exclude '__pycache__' "$REPO_ROOT/$pkg/" "$dest/$pkg/"
  done
  echo "Synced $* into $dest"
}

# AgentCore coordinator bundle (AWS): needs the coordinator and its MCP client.
sync_into "$REPO_ROOT/app/CurrencyCoordinator" coordinator mcp_server
# Foundry A2A peer bundle (Azure): serves rates from the MCP stdio server,
# which imports the domain models and providers from coordinator/.
sync_into "$REPO_ROOT/foundry_agent" coordinator mcp_server
