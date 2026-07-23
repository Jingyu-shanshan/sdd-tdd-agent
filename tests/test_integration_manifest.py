import io
import json
from pathlib import Path

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.integration_api import (
    MODEL_OPERATIONS,
    build_integration_manifest,
    render_integration_manifest,
)


def test_should_publish_versioned_plugin_and_ide_contract() -> None:
    manifest = build_integration_manifest()

    assert set(manifest) == {"schema_version", "plugin_api", "ide_api", "providers"}
    assert manifest["schema_version"] == 1
    assert manifest["plugin_api"] == {
        "execution": "external-process",
        "protocol": "json-command",
        "request_transport": "json-stdin",
        "response_transport": "json-stdout",
        "operations": list(MODEL_OPERATIONS),
        "configuration": ".agent/config.yml",
        "requires_explicit_selection": True,
    }
    assert manifest["ide_api"] == {
        "execution": "cli-process",
        "commands": {
            "project_memory": ["wssagent", "memory"],
            "provider_status": ["wssagent", "provider", "status"],
            "status": ["wssagent", "status"],
        },
        "exit_codes": {"success": 0, "error": 2},
    }


def test_should_derive_provider_capabilities_in_registry_order() -> None:
    providers = build_integration_manifest()["providers"]

    assert providers == [
        {"key": "codex", "status": "adapter-ready", "protocol": "codex-exec"},
        {
            "key": "custom-json",
            "status": "adapter-ready",
            "protocol": "json-command",
        },
        {
            "key": "claude-code",
            "status": "adapter-ready",
            "protocol": "claude-exec",
        },
        {
            "key": "cursor",
            "status": "adapter-ready",
            "protocol": "cursor-exec",
        },
        {"key": "copilot", "status": "planned", "protocol": None},
    ]


def test_should_render_deterministic_manifest_through_cli(tmp_path: Path) -> None:
    expected = render_integration_manifest(build_integration_manifest())
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["integration", "manifest"],
        out=output,
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == expected
    assert json.loads(output.getvalue()) == build_integration_manifest()
    assert error_output.getvalue() == ""
    assert not (tmp_path / ".agent").exists()
