import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, TextIO, Tuple

from sdd_tdd_agent.analyze_command import load_analyzer_config
from sdd_tdd_agent.model_adapter import ProcessRunner
from sdd_tdd_agent.provider_registry import (
    ProviderInstallPlan,
    ProviderSelection,
    get_provider,
    select_provider,
    validate_provider_selection,
)


class ProviderExecutableLocator(Protocol):
    """Typed boundary for locating one provider executable."""

    def locate(self, executable: str) -> Optional[str]:
        """Return an executable path/token when available, otherwise None."""
        ...


@dataclass(frozen=True)
class ProviderCommandDependencies:
    """Injected process, executable, and input boundaries for provider CLI work."""

    input: TextIO
    runner: ProcessRunner
    locator: ProviderExecutableLocator
    platform: str = sys.platform


@dataclass(frozen=True)
class ProviderDiagnostic:
    """Read-only adapter and CLI health for one known provider."""

    provider_key: str
    adapter_status: str
    cli_status: str
    version: Optional[str]


@dataclass(frozen=True)
class ProviderInstallResult:
    """Verified result of one explicitly confirmed provider installation."""

    provider_key: str
    version: str


class ProviderInstallError(RuntimeError):
    """Safe error raised by guarded provider installation."""


@dataclass(frozen=True)
class ProviderUseResult:
    """Result of interactive or non-interactive provider selection."""

    selection: Optional[ProviderSelection]
    installed_version: Optional[str]
    cancelled: bool


class ProviderDoctor:
    """Diagnose provider lifecycle and executable version health."""

    def __init__(
        self,
        runner: ProcessRunner,
        locator: ProviderExecutableLocator,
        timeout_seconds: float,
    ) -> None:
        self._runner = runner
        self._locator = locator
        self._timeout_seconds = timeout_seconds

    def diagnose(self, provider_key: str) -> ProviderDiagnostic:
        """Diagnose one provider without mutating configuration or state."""
        provider = get_provider(provider_key)
        if provider.status != "adapter-ready":
            return ProviderDiagnostic(
                provider.key,
                provider.status,
                "not-checked",
                None,
            )
        if provider.command is None:
            return ProviderDiagnostic(
                provider.key,
                provider.status,
                "manual-configuration",
                None,
            )
        executable = self._locator.locate(provider.command[0])
        if executable is None:
            return ProviderDiagnostic(
                provider.key,
                provider.status,
                "missing",
                None,
            )
        result = self._runner.run(
            (executable, "--version"),
            "",
            self._timeout_seconds,
        )
        version = _safe_version(result.stdout)
        if result.returncode != 0 or version is None:
            return ProviderDiagnostic(
                provider.key,
                provider.status,
                "unhealthy",
                None,
            )
        return ProviderDiagnostic(
            provider.key,
            provider.status,
            "installed",
            version,
        )


def _safe_version(stdout: str) -> Optional[str]:
    lines: Tuple[str, ...] = tuple(stdout.strip().splitlines())
    if (
        len(lines) != 1
        or not lines[0]
        or len(lines[0]) > 200
        or not lines[0].isprintable()
    ):
        return None
    return lines[0]


def render_provider_diagnostic(diagnostic: ProviderDiagnostic) -> str:
    """Render deterministic provider health without process details."""
    output = (
        f"Provider: {diagnostic.provider_key}\n"
        f"Adapter status: {diagnostic.adapter_status}\n"
        f"CLI status: {diagnostic.cli_status}\n"
    )
    if diagnostic.version is not None:
        output += f"Version: {diagnostic.version}\n"
    return output


class ProviderInstaller:
    """Download, install, and verify one Registry-approved provider CLI."""

    def __init__(
        self,
        runner: ProcessRunner,
        locator: ProviderExecutableLocator,
        timeout_seconds: float,
        platform: str = sys.platform,
    ) -> None:
        self._runner = runner
        self._locator = locator
        self._timeout_seconds = timeout_seconds
        self._platform = platform

    def install(self, provider_key: str) -> ProviderInstallResult:
        """Execute one verified install plan after caller confirmation."""
        provider = get_provider(provider_key)
        if provider.status != "adapter-ready" or provider.command is None:
            raise ProviderInstallError("Provider adapter is not installable")
        if provider.install_plan is None:
            raise ProviderInstallError("Provider has no verified install plan")
        _validate_install_platform(provider.platforms, self._platform)
        try:
            with tempfile.TemporaryDirectory(prefix="sdd-tdd-provider-") as directory:
                script_path = Path(directory) / "install.sh"
                self._download(provider.install_plan, script_path)
                self._execute(provider.install_plan, script_path)
                version = self._verify(provider.command[0])
        except OSError as error:
            raise ProviderInstallError(
                "Provider installer temporary files are unavailable"
            ) from error
        return ProviderInstallResult(provider.key, version)

    def _download(self, plan: ProviderInstallPlan, script_path: Path) -> None:
        command = plan.download_command + (str(script_path), plan.source_url)
        result = self._runner.run(command, "", self._timeout_seconds)
        if result.returncode != 0:
            raise ProviderInstallError("Provider installer download failed")
        if not script_path.is_file():
            raise ProviderInstallError("Provider installer download is missing")

    def _execute(self, plan: ProviderInstallPlan, script_path: Path) -> None:
        command = plan.installer_command + (str(script_path),)
        result = self._runner.run(command, "", self._timeout_seconds)
        if result.returncode != 0:
            raise ProviderInstallError("Provider installer execution failed")

    def _verify(self, executable_name: str) -> str:
        executable = self._locator.locate(executable_name)
        if executable is None:
            raise ProviderInstallError("Installed provider CLI could not be located")
        result = self._runner.run(
            (executable, "--version"),
            "",
            self._timeout_seconds,
        )
        version = _safe_version(result.stdout)
        if result.returncode != 0 or version is None:
            raise ProviderInstallError("Installed provider CLI verification failed")
        return version


def use_provider(
    root: Path,
    provider_key: str,
    dependencies: ProviderCommandDependencies,
    output: TextIO,
) -> ProviderUseResult:
    """Select a provider, installing a missing CLI only after TTY confirmation."""
    provider = validate_provider_selection(provider_key)
    if provider.command is None:
        raise ProviderInstallError("Provider adapter command is unavailable")
    executable_name = provider.command[0]
    config = load_analyzer_config(root)
    if not dependencies.input.isatty():
        selection = select_provider(root, provider.key)
        return ProviderUseResult(selection, None, False)
    executable = dependencies.locator.locate(executable_name)
    if executable is not None:
        selection = select_provider(root, provider.key)
        return ProviderUseResult(selection, None, False)
    _validate_install_platform(provider.platforms, dependencies.platform)
    output.write(
        f"Provider CLI '{executable_name}' was not found. "
        "Install the current stable CLI from the official source? [y/N] "
    )
    answer = dependencies.input.readline().strip().lower()
    if answer not in {"y", "yes"}:
        return ProviderUseResult(None, None, True)
    installed = ProviderInstaller(
        runner=dependencies.runner,
        locator=dependencies.locator,
        timeout_seconds=config.timeout_seconds,
        platform=dependencies.platform,
    ).install(provider.key)
    selection = select_provider(root, provider.key)
    return ProviderUseResult(selection, installed.version, False)


def _validate_install_platform(
    supported_platforms: Tuple[str, ...],
    platform: str,
) -> None:
    platform_key = {"darwin": "macos", "linux": "linux-mint"}.get(platform)
    if platform_key is None or platform_key not in supported_platforms:
        raise ProviderInstallError(
            "Provider installer is not supported on this platform"
        )
