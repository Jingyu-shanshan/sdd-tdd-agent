import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from sdd_tdd_agent.analyze_command import (
    AnalyzerConfigurationError,
    COMMAND_KEY,
    PROTOCOL_KEY,
    TIMEOUT_KEY,
    load_analyzer_config,
)
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig


@dataclass(frozen=True)
class ProviderInstallPlan:
    """Verified tokenized download and execution plan for one provider CLI."""

    source_url: str
    download_command: Tuple[str, ...]
    installer_command: Tuple[str, ...]


@dataclass(frozen=True)
class ProviderDefinition:
    """One known agent provider and its adapter lifecycle metadata."""

    key: str
    display_name: str
    status: str
    platforms: Tuple[str, ...]
    protocol: Optional[str] = None
    command: Optional[Tuple[str, ...]] = None
    install_plan: Optional[ProviderInstallPlan] = None


@dataclass(frozen=True)
class ProviderSelection:
    """One provider selected by the current analyzer configuration."""

    provider_key: str
    status: str
    protocol: str
    timeout_seconds: float
    role: Optional[str] = None


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
        install_plan=ProviderInstallPlan(
            source_url="https://chatgpt.com/codex/install.sh",
            download_command=("curl", "-fsSL", "--output"),
            installer_command=("sh",),
        ),
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
        status="adapter-ready",
        platforms=("macos", "linux-mint"),
        protocol="claude-exec",
        command=("claude",),
        install_plan=ProviderInstallPlan(
            source_url="https://claude.ai/install.sh",
            download_command=("curl", "-fsSL", "--output"),
            installer_command=("sh",),
        ),
    ),
    ProviderDefinition(
        key="cursor",
        display_name="Cursor",
        status="adapter-ready",
        platforms=("macos", "linux-mint"),
        protocol="cursor-exec",
        command=("cursor-agent",),
        install_plan=ProviderInstallPlan(
            source_url="https://cursor.com/install",
            download_command=("curl", "-fsSL", "--output"),
            installer_command=("sh",),
        ),
    ),
    ProviderDefinition(
        key="pi",
        display_name="Pi Coding Agent",
        status="adapter-ready",
        platforms=("macos", "linux-mint"),
        protocol="pi-exec",
        command=("pi",),
        install_plan=ProviderInstallPlan(
            source_url="https://pi.dev/install.sh",
            download_command=("curl", "-fsSL", "--output"),
            installer_command=("sh",),
        ),
    ),
    ProviderDefinition(
        key="copilot",
        display_name="GitHub Copilot",
        status="planned",
        platforms=(),
    ),
)

PROVIDER_ROLE_KEYS = {
    "test-source": "test_source_provider",
    "production-source": "production_source_provider",
}
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 300.0


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


def load_provider_selection(
    root: Path,
    role: Optional[str] = None,
) -> ProviderSelection:
    """Load the selected provider without executing or resolving its command."""
    config = load_provider_config(root, role) if role else load_analyzer_config(root)
    provider_keys = {
        "codex-exec": "codex",
        "claude-exec": "claude-code",
        "cursor-exec": "cursor",
        "pi-exec": "pi",
    }
    provider_key = provider_keys.get(config.protocol, "custom-json")
    provider = next(item for item in PROVIDERS if item.key == provider_key)
    return ProviderSelection(
        provider_key=provider.key,
        status=provider.status,
        protocol=config.protocol,
        timeout_seconds=config.timeout_seconds,
        role=role,
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
    return get_provider(provider_key)


def get_provider(provider_key: str) -> ProviderDefinition:
    """Return one known provider or raise a safe selection error."""
    for provider in PROVIDERS:
        if provider.key == provider_key:
            return provider
    raise ProviderSelectionError(f"Unknown provider: {provider_key}")


def _provider_role_key(role: str) -> str:
    try:
        return PROVIDER_ROLE_KEYS[role]
    except KeyError as error:
        raise ProviderSelectionError(f"Unknown provider role: {role}") from error


def _load_role_provider(root: Path, role: str) -> Optional[ProviderDefinition]:
    key = _provider_role_key(role)
    selected: Optional[str] = None
    for line in (
        (root / ".agent" / "config.yml").read_text(encoding="utf-8").splitlines()
    ):
        if not line or line[0].isspace():
            continue
        name, separator, value = line.partition(":")
        if name != key:
            continue
        if selected is not None or not separator or not value.strip():
            raise ProviderSelectionError(f"Invalid provider role config: {role}")
        selected = value.strip()
    if selected is None:
        return None
    return validate_provider_selection(selected)


def load_provider_config(root: Path, role: str) -> CommandAnalyzerConfig:
    """Load a role-specific provider config, falling back to the default."""
    default = load_analyzer_config(root)
    provider = _load_role_provider(root, role)
    if provider is None:
        return default
    if provider.command is None or provider.protocol is None:
        raise ProviderSelectionError(f"Provider is not configured: {provider.key}")
    return CommandAnalyzerConfig(
        provider.command,
        default.timeout_seconds,
        provider.protocol,
    )


def validate_provider_role(root: Path, role: str) -> None:
    """Validate one configured Provider role without loading the default."""
    _provider_role_key(role)
    _load_role_provider(root, role)


def _validate_selectable(provider: ProviderDefinition) -> None:
    if provider.status != "adapter-ready":
        raise ProviderSelectionError(
            f"Provider is not selectable: {provider.key} ({provider.status})"
        )
    if provider.protocol is None or provider.command is None:
        raise ProviderSelectionError(
            f"Provider requires explicit command configuration: {provider.key}"
        )


def validate_provider_selection(provider_key: str) -> ProviderDefinition:
    """Validate and return one fully configured adapter-ready provider."""
    provider = get_provider(provider_key)
    _validate_selectable(provider)
    return provider


def _provider_config(content: str, provider: ProviderDefinition) -> str:
    lines = content.splitlines()
    if not _has_analyzer_config(lines):
        lines.extend(
            (
                f"{PROTOCOL_KEY}: {provider.protocol}",
                f"{COMMAND_KEY}:",
                *(f"  - {json.dumps(argument)}" for argument in provider.command or ()),
                f"{TIMEOUT_KEY}: {DEFAULT_PROVIDER_TIMEOUT_SECONDS:g}",
            )
        )
        return "\n".join(lines) + "\n"
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


def _has_analyzer_config(lines: List[str]) -> bool:
    keys = (COMMAND_KEY, PROTOCOL_KEY, TIMEOUT_KEY)
    return any(line.startswith(f"{key}:") for line in lines for key in keys)


def load_provider_selection_config(root: Path) -> CommandAnalyzerConfig:
    """Load strict configuration or defaults for an initialized project."""
    path = root / ".agent" / "config.yml"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise AnalyzerConfigurationError(
            "Project is not initialized; run 'wssagent init' in the project root"
        ) from error
    if _has_analyzer_config(lines):
        return load_analyzer_config(root)
    if not lines:
        raise AnalyzerConfigurationError("Analyzer configuration is incomplete")
    return CommandAnalyzerConfig(
        ("codex",),
        DEFAULT_PROVIDER_TIMEOUT_SECONDS,
        "codex-exec",
    )


def _provider_role_config(
    content: str,
    provider: ProviderDefinition,
    role: str,
) -> str:
    key = _provider_role_key(role)
    lines = content.splitlines()
    replacement = f"{key}: {provider.key}"
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[index] = replacement
            return "\n".join(lines) + "\n"
    lines.append(replacement)
    return "\n".join(lines) + "\n"


def select_provider(
    root: Path,
    provider_key: str,
    role: Optional[str] = None,
) -> ProviderSelection:
    """Atomically select one adapter-ready provider in tracked configuration."""
    current = load_provider_selection_config(root)
    if role is not None:
        validate_provider_role(root, role)
    provider = _find_provider(provider_key)
    _validate_selectable(provider)
    config_path = root / ".agent" / "config.yml"
    content = config_path.read_text(encoding="utf-8")
    if role is None:
        updated = _provider_config(content, provider)
    else:
        if not _has_analyzer_config(content.splitlines()):
            content = _provider_config(content, _find_provider("codex"))
        updated = _provider_role_config(content, provider, role)
    temporary = config_path.with_name(".config.yml.provider.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(config_path)
    return ProviderSelection(
        provider_key=provider.key,
        status=provider.status,
        protocol=provider.protocol or current.protocol,
        timeout_seconds=current.timeout_seconds,
        role=role,
    )
