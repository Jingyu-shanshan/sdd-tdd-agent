import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from sdd_tdd_agent.analyze_command import load_analyzer_config


@dataclass(frozen=True)
class ProviderDefinition:
    """One known agent provider and its adapter lifecycle metadata."""

    key: str
    display_name: str
    status: str
    platforms: Tuple[str, ...]
    protocol: Optional[str] = None
    command: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class ProviderSelection:
    """One provider selected by the current analyzer configuration."""

    provider_key: str
    status: str
    protocol: str
    timeout_seconds: float


class ProviderSelectionError(ValueError):
    """Safe error raised when a provider cannot be selected."""


PROVIDERS = (
    ProviderDefinition(
        key="codex",
        display_name="OpenAI Codex CLI",
        status="adapter-ready",
        platforms=("macos", "linux-mint"),
        protocol="codex-exec",
        command=("codex",),
    ),
    ProviderDefinition(
        key="custom-json",
        display_name="Custom JSON command",
        status="adapter-ready",
        platforms=("macos", "linux-mint"),
        protocol="json-command",
    ),
    ProviderDefinition(
        key="claude-code",
        display_name="Claude Code",
        status="planned",
        platforms=(),
    ),
    ProviderDefinition(
        key="cursor",
        display_name="Cursor",
        status="planned",
        platforms=(),
    ),
    ProviderDefinition(
        key="copilot",
        display_name="GitHub Copilot",
        status="planned",
        platforms=(),
    ),
)


def list_providers() -> Tuple[ProviderDefinition, ...]:
    """Return all known providers in deterministic display order."""
    return PROVIDERS


def render_provider_list(providers: Tuple[ProviderDefinition, ...]) -> str:
    """Render deterministic provider lifecycle and platform information."""
    lines = []
    for provider in providers:
        platforms = ", ".join(provider.platforms)
        platform_text = platforms or "platform contract pending"
        lines.append(
            f"{provider.key}: {provider.status} ({platform_text}) - "
            f"{provider.display_name}"
        )
    return "\n".join(lines) + "\n"


def load_provider_selection(root: Path) -> ProviderSelection:
    """Load the selected provider without executing or resolving its command."""
    config = load_analyzer_config(root)
    provider_key = "codex" if config.protocol == "codex-exec" else "custom-json"
    provider = next(item for item in PROVIDERS if item.key == provider_key)
    return ProviderSelection(
        provider_key=provider.key,
        status=provider.status,
        protocol=config.protocol,
        timeout_seconds=config.timeout_seconds,
    )


def render_provider_status(selection: ProviderSelection) -> str:
    """Render deterministic selected-provider configuration status."""
    return (
        f"Selected provider: {selection.provider_key}\n"
        f"Adapter status: {selection.status}\n"
        f"Protocol: {selection.protocol}\n"
        f"Timeout seconds: {selection.timeout_seconds:g}\n"
    )


def _find_provider(provider_key: str) -> ProviderDefinition:
    for provider in PROVIDERS:
        if provider.key == provider_key:
            return provider
    raise ProviderSelectionError(f"Unknown provider: {provider_key}")


def _validate_selectable(provider: ProviderDefinition) -> None:
    if provider.status != "adapter-ready":
        raise ProviderSelectionError(
            f"Provider is not selectable: {provider.key} ({provider.status})"
        )
    if provider.protocol is None or provider.command is None:
        raise ProviderSelectionError(
            f"Provider requires explicit command configuration: {provider.key}"
        )


def _provider_config(content: str, provider: ProviderDefinition) -> str:
    lines = content.splitlines()
    rendered: List[str] = []
    has_protocol = any(
        line.startswith("requirement_analyzer_protocol:") for line in lines
    )
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("requirement_analyzer_protocol:"):
            rendered.append(f"requirement_analyzer_protocol: {provider.protocol}")
            index += 1
            continue
        if line.startswith("requirement_analyzer_command:"):
            if not has_protocol:
                rendered.append(f"requirement_analyzer_protocol: {provider.protocol}")
            rendered.append("requirement_analyzer_command:")
            for argument in provider.command or ():
                rendered.append(f"  - {json.dumps(argument)}")
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if candidate and not candidate[0].isspace():
                    break
                if not candidate:
                    rendered.append(candidate)
                index += 1
            continue
        rendered.append(line)
        index += 1
    return "\n".join(rendered) + "\n"


def select_provider(root: Path, provider_key: str) -> ProviderSelection:
    """Atomically select one adapter-ready provider in tracked configuration."""
    provider = _find_provider(provider_key)
    _validate_selectable(provider)
    current = load_analyzer_config(root)
    config_path = root / ".agent" / "config.yml"
    updated = _provider_config(config_path.read_text(encoding="utf-8"), provider)
    temporary = config_path.with_name(".config.yml.provider.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(config_path)
    return ProviderSelection(
        provider_key=provider.key,
        status=provider.status,
        protocol=provider.protocol or current.protocol,
        timeout_seconds=current.timeout_seconds,
    )
