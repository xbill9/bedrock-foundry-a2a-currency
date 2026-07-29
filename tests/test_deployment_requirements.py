from pathlib import Path
import tomllib

import yaml


def test_agentcore_requirements_include_async_entra_transport() -> None:
    """The hosted Foundry token provider needs azure-core's aiohttp transport."""
    requirements = (Path(__file__).parents[1] / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert any(
        line.startswith("aiohttp==")
        for line in requirements.splitlines()
        if line and not line.startswith("#")
    )

    app_manifest = Path(__file__).parents[1] / "app" / "CurrencyCoordinator" / "pyproject.toml"
    app = tomllib.loads(app_manifest.read_text(encoding="utf-8"))
    dependencies = app["project"]["dependencies"]

    assert any(dependency.startswith("aiohttp ") for dependency in dependencies)


def test_foundry_hosted_agent_has_a_concrete_model_name() -> None:
    manifest_path = Path(__file__).parents[1] / "foundry_agent" / "azure.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    environment = manifest["services"]["currency-a2a-agent"]["environmentVariables"]
    values = {item["name"]: item["value"] for item in environment}

    assert values["AZURE_AI_MODEL_DEPLOYMENT_NAME"] == "gpt-5-mini"


def test_coordinator_prompt_classifies_the_foundry_peer_as_live() -> None:
    entrypoint = (
        Path(__file__).parents[1] / "app" / "CurrencyCoordinator" / "main.py"
    ).read_text(encoding="utf-8")

    assert "'hosted-foundry-a2a' is live" in entrypoint
