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


@dataclass(frozen=True)
class ProviderRolesStatus:
    """Configured public Provider roles for one project."""

    code_provider: Optional[str]
    test_provider: Optional[str]
    test_inherited: bool


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
    config = (
        load_provider_config(root, role) if role else load_primary_provider_config(root)
    )
    provider_key = _provider_key_for_protocol(config.protocol)
    provider = next(item for item in PROVIDERS if item.key == provider_key)
    return ProviderSelection(
        provider_key=provider.key,
        status=provider.status,
        protocol=config.protocol,
        timeout_seconds=config.timeout_seconds,
        role=role,
    )


def _provider_key_for_protocol(protocol: str) -> str:
    return {
        "codex-exec": "codex",
        "claude-exec": "claude-code",
        "cursor-exec": "cursor",
        "pi-exec": "pi",
    }.get(protocol, "custom-json")


def render_provider_status(selection: ProviderSelection) -> str:
    """Render deterministic selected-provider configuration status."""
    return (
        f"Selected provider: {selection.provider_key}\n"
        f"Adapter status: {selection.status}\n"
        f"Protocol: {selection.protocol}\n"
        f"Timeout seconds: {selection.timeout_seconds:g}\n"
    )


def load_provider_roles_status(root: Path) -> ProviderRolesStatus:
    """Load public Provider roles without mutating project configuration."""
    fallback = load_provider_selection_config(root)
    content = (root / ".agent" / "config.yml").read_text(encoding="utf-8")
    code = _load_role_provider(root, "production-source")
    if code is None and _has_analyzer_config(content.splitlines()):
        code_key: Optional[str] = _provider_key_for_protocol(fallback.protocol)
    else:
        code_key = code.key if code is not None else None
    test = _load_role_provider(root, "test-source")
    test_key = test.key if test is not None else code_key
    return ProviderRolesStatus(
        code_provider=code_key,
        test_provider=test_key,
        test_inherited=test is None and test_key is not None,
    )


def render_provider_roles_status(status: ProviderRolesStatus) -> str:
    """Render the two public Provider roles."""
    code = status.code_provider or "not configured"
    test = status.test_provider or "not configured"
    inherited = " (inherited)" if status.test_inherited else ""
    return f"Code provider: {code}\nTest provider: {test}{inherited}\n"


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
    """Load a public role, with test inheriting the primary code Provider."""
    _provider_role_key(role)
    if role == "production-source":
        return load_primary_provider_config(root)
    provider = _load_role_provider(root, role)
    if provider is None:
        return load_primary_provider_config(root)
    default = load_provider_selection_config(root)
    if provider.command is None or provider.protocol is None:
        raise ProviderSelectionError(f"Provider is not configured: {provider.key}")
    return CommandAnalyzerConfig(
        provider.command,
        default.timeout_seconds,
        provider.protocol,
    )


def load_primary_provider_config(root: Path) -> CommandAnalyzerConfig:
    """Load the code Provider, falling back only to explicit legacy config."""
    fallback = load_provider_selection_config(root)
    provider = _load_role_provider(root, "production-source")
    if provider is not None:
        if provider.command is None or provider.protocol is None:
            raise ProviderSelectionError(f"Provider is not configured: {provider.key}")
        return CommandAnalyzerConfig(
            provider.command,
            fallback.timeout_seconds,
            provider.protocol,
        )
    content = (root / ".agent" / "config.yml").read_text(encoding="utf-8")
    if not _has_analyzer_config(content.splitlines()):
        raise AnalyzerConfigurationError(
            "Code provider is not configured; run "
            "'wssagent provider use <provider> --for code'"
        )
    return fallback


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
    elif role == "production-source":
        updated = _provider_role_config(
            _provider_config(content, provider),
            provider,
            role,
        )
    else:
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
