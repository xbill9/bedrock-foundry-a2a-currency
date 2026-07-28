# Microsoft Foundry A2A agent

The Azure counterpart of `adk_agent/`: the same benchmark contract served by a
different vendor's framework, so the coordinator's A2A leg can be measured
against Google ADK and Microsoft Foundry without changing the coordinator.

```text
AgentCore coordinator (AWS) --A2A v1.0 / JSONRPC + Entra--> this agent (Azure)
                                                                 |
                                                                 +-- MCP stdio --> Frankfurter
```

## What Foundry requires

Incoming A2A is a preview feature with hard constraints, all of which shaped
this directory and `coordinator/a2a_peers.py`:

- **The responses protocol is mandatory.** A hosted agent can only be exposed
  over A2A if it implements it, which is why `main.py` serves through
  `ResponsesHostServer` rather than a plain HTTP app.
- **The agent card is not at the well-known path.** It is published at
  `…/endpoint/protocols/a2a/agentCard/v1.0`; the coordinator passes that as
  `agent_card_path` instead of `/.well-known/agent-card.json`.
- **Every A2A URL needs Microsoft Entra authentication**, the card included.
  Keys and anonymous access are not supported, so unlike the Cloud Run ADK
  agent this peer cannot be smoke-tested with `curl` alone.
- **v1.0 must be pinned.** Foundry serves A2A v0.3 by default; the coordinator
  sends `A2A-Version: 1.0` on every request rather than relying on card
  negotiation.
- **JSONRPC only, no streaming, text only** for v1.0.

## Deploy

One command from the repo root, which syncs the bundle, provisions, deploys,
and enables incoming A2A:

```bash
az login && azd auth login
./infra/deploy_foundry_peer.sh
```

Or step by step:

```bash
./infra/sync_app.sh                 # copy coordinator/ + mcp_server/ into this directory
cd foundry_agent && azd provision && azd deploy
cd .. && FOUNDRY_PROJECT_ENDPOINT=... python3 infra/enable_foundry_a2a.py
```

`enable_foundry_a2a.py` prints the A2A base URL to export as
`CURRENCY_FOUNDRY_A2A_ENDPOINT`. The calling identity then needs the **Foundry
Agent Consumer** role on the project; see `../infra/README.md` for the AWS-side
credential wiring.

## Notes

- `coordinator/` and `mcp_server/` in this directory are build artifacts synced
  by `infra/sync_app.sh` and are gitignored. Edit the repo-root packages.
- The MCP rate server runs as a child process of this container
  (`python -m mcp_server.server` over stdio), mirroring the ADK agent's
  colocated MCP server so the remote peer's tool hop is MCP on both sides.
- `CURRENCY_RATE_PROVIDER` defaults to `frankfurter` here, not `fixture`: a
  remote verifier answering with fixture rates would make verified mode
  meaningless.
- The agent copies the tool's decimal strings through verbatim. Rounding in the
  model's reply shows up as a verified-mode disagreement, not as a silent error.

## Current platform references

- [Enable incoming A2A on a Foundry agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint)
- [Host Microsoft Agent Framework agents in Foundry](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents)
- [Agent2Agent authentication](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-to-agent-authentication)
