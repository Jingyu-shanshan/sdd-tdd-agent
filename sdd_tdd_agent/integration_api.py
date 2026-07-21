import json
from typing import Dict, List, Tuple

from sdd_tdd_agent.provider_registry import list_providers


MODEL_OPERATIONS: Tuple[str, ...] = (
    "requirement_analysis",
    "design_generation",
    "task_breakdown",
    "test_generation",
    "test_source_generation",
    "production_source_generation",
    "semantic_review",
    "automated_refactor",
)


def _provider_capabilities() -> List[Dict[str, object]]:
    return [
        {
            "key": provider.key,
            "status": provider.status,
            "protocol": provider.protocol,
        }
        for provider in list_providers()
    ]


def build_integration_manifest() -> Dict[str, object]:
    """Build the immutable versioned plugin and IDE discovery contract."""
    return {
        "schema_version": 1,
        "plugin_api": {
            "execution": "external-process",
            "protocol": "json-command",
            "request_transport": "json-stdin",
            "response_transport": "json-stdout",
            "operations": list(MODEL_OPERATIONS),
            "configuration": ".agent/config.yml",
            "requires_explicit_selection": True,
        },
        "ide_api": {
            "execution": "cli-process",
            "commands": {
                "project_memory": ["agent", "memory"],
                "provider_status": ["agent", "provider", "status"],
                "status": ["agent", "status"],
            },
            "exit_codes": {"success": 0, "error": 2},
        },
        "providers": _provider_capabilities(),
    }


def render_integration_manifest(manifest: Dict[str, object]) -> str:
    """Render deterministic machine-readable integration discovery JSON."""
    return f"{json.dumps(manifest, indent=2, sort_keys=True)}\n"
