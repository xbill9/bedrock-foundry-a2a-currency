"""Microsoft Foundry hosted currency agent, called from AWS over A2A v1.0.

This is the Azure counterpart of ``adk_agent/``: the same benchmark contract
(one JSON quote object per requested target currency) served by a different
vendor's agent framework, so the coordinator's A2A leg can be measured against
Google ADK and Microsoft Foundry without changing the coordinator.

Shape of the deployment:

- Microsoft Agent Framework ``Agent`` on a Foundry model deployment;
- rates fetched through MCP — the repo's ``mcp_server`` stdio server runs as a
  child process of this container, mirroring the ADK agent's colocated MCP
  server, so the remote peer's tool hop is MCP on both sides;
- ``ResponsesHostServer`` provides the responses protocol, which Foundry
  requires before incoming A2A can be enabled on a hosted agent
  (``infra/enable_foundry_a2a.py`` turns it on and publishes the agent card).

The agent never does arithmetic itself: the MCP tool returns exact decimal
strings and the model is instructed to copy them through.
"""

import os
import sys

from agent_framework import Agent, MCPStdioTool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential

INSTRUCTION = (
    "You are a specialized assistant for currency conversions. "
    "Your sole purpose is to use the 'convert_currency' tool to answer questions about "
    "currency exchange rates. "
    "When asked to convert an amount, call the tool once for each requested target "
    "currency, then reply with exactly one JSON object per line of the form "
    '{"source_currency": "<ISO code>", "target_currency": "<ISO code>", '
    '"rate": <decimal>, "converted_amount": <decimal>} '
    "and no other text. "
    "Copy the tool's rate and converted_amount digits exactly; never round them and "
    "never compute them yourself. "
    "If the user asks about anything other than currency conversion or exchange rates, "
    "politely state that you cannot help with that topic."
)

DESCRIPTION = "Answers currency conversion questions with structured decimal quotes."


def mcp_environment() -> dict[str, str]:
    """Environment for the MCP child process.

    The child inherits nothing implicitly, so pass the interpreter's search
    path along with the rate-provider selection. ``frankfurter`` is the default
    here (unlike the coordinator, which defaults to fixtures) because a remote
    peer that answers with fixture rates would make verified mode meaningless.
    """
    env = {
        "CURRENCY_RATE_PROVIDER": os.getenv("CURRENCY_RATE_PROVIDER", "frankfurter"),
        "PATH": os.getenv("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONPATH": os.getenv("PYTHONPATH", os.getcwd()),
        "PYTHONUNBUFFERED": "1",
    }
    if home := os.getenv("HOME"):
        env["HOME"] = home
    return env


def build_rate_tool() -> MCPStdioTool:
    return MCPStdioTool(
        name="currency_rates",
        description="Live exchange rates and exact decimal conversions.",
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=mcp_environment(),
        # The fixture server advertises tools only; asking it for prompts
        # would draw a JSON-RPC method-not-found.
        load_prompts=False,
    )


def build_agent() -> Agent:
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )
    return Agent(
        client=client,
        name="currency-a2a-agent",
        description=DESCRIPTION,
        instructions=INSTRUCTION,
        tools=[build_rate_tool()],
        # A2A callers send one self-contained request per conversion; storing
        # server-side state would only add latency to the measurement.
        default_options={"store": False},
    )


def main() -> None:
    ResponsesHostServer(build_agent()).run()


if __name__ == "__main__":
    main()
