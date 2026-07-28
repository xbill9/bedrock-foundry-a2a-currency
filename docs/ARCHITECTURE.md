# Architecture and trust boundaries

## Components

1. **Client** submits a structured conversion request.
2. **AgentCore-hosted coordinator** uses Strands Agents on an Amazon Bedrock
   model to choose the benchmark path and produce the final explanation.
3. **MCP server** obtains a timestamped exchange rate and performs deterministic
   decimal arithmetic.
4. **Remote A2A agent** independently calculates or verifies the conversion and
   is invoked through A2A v1.0. Two are interchangeable per run: a Google ADK
   agent on Cloud Run and a Microsoft Foundry hosted agent. The coordinator
   holds one client; `coordinator/a2a_peers.py` holds the vendor differences.
5. **Comparator** checks identity fields and relative numeric difference without
   asking a model to judge arithmetic.
6. **Evaluation runner** captures correctness, latency, cost, failures, versions,
   and trace correlation.

## Trust boundaries

- The client input is untrusted.
- MCP tool descriptions and outputs are untrusted model context.
- A2A cards and remote-agent messages are untrusted remote content.
- Authentication proves an identity, not the correctness of returned data.
- Model prose is never the system of record for amounts or rates.
- Secrets must remain in AWS IAM/execution roles, GCP Secret Manager, and AWS
  Secrets Manager; the coordinator container carries no long-lived keys and no
  Azure credential in its committed runtime configuration.
- A bearer token proves the caller to Foundry; it says nothing about the
  quotes that come back, which are compared numerically like any other source.

## Failure policy

- If MCP fails and A2A succeeds, return a clearly labeled unverified remote result.
- If A2A fails and MCP succeeds, return the tool result with verification missing.
- If both succeed but disagree beyond tolerance, return both and warn; never
  silently choose the model's preferred answer.
- If both fail, return a typed failure without fabricating a rate.
- If the rate is stale, show its timestamp and flag it.

## Platform constraints to test and document

- AgentCore Runtime invokes the coordinator through its own HTTP contract
  (`/invocations`), so the A2A hop in this lab is outbound only: the
  coordinator is an A2A client of the remote agents.
- Cross-cloud egress: the AgentCore container must reach Cloud Run, the
  Foundry data plane, and the Frankfurter API over the public internet.
- Cross-cloud identity is asymmetric. The ADK peer is anonymous; the Foundry
  peer requires a Microsoft Entra token on every request, agent card included,
  and rejects keys. An AWS-hosted caller therefore needs a service principal,
  read from AWS Secrets Manager at call time (`coordinator/entra_auth.py`) and
  cached until shortly before expiry so credential acquisition is not charged
  to the measured A2A latency.
- Foundry's incoming A2A is preview: v1.0 is JSONRPC-only, text-only, no
  streaming, requires the responses protocol, publishes its card at
  `agentCard/v1.0`, and serves v0.3 unless the caller pins the version.
- SDK package names, IAM permissions, and deployment shapes may change;
  pin versions once an end-to-end deployment is verified.
