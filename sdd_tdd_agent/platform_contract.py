import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Protocol, Tuple


MINIMUM_PYTHON_VERSION = (3, 9)
OS_RELEASE_KEY = re.compile(r"[A-Z][A-Z0-9_]*")
DEFAULT_OS_RELEASE_PATHS = (Path("/etc/os-release"), Path("/usr/lib/os-release"))
SYSTEM_PYTHON_VERSION = (
    sys.version_info.major,
    sys.version_info.minor,
    sys.version_info.micro,
)


class PlatformContractError(ValueError):
    """Safe error raised for invalid platform identification data."""


class PlatformEnvironment(Protocol):
    """Typed read-only boundary for host platform capabilities."""

    def system_name(self) -> str:
        """Return a normalized runtime system identifier."""
        ...

    def python_version(self) -> Tuple[int, int, int]:
        """Return the active Python major, minor, and micro version."""
        ...

    def os_release(self) -> Optional[str]:
        """Return Linux os-release content when available."""
        ...

    def temporary_directory_available(self) -> bool:
        """Return whether a private temporary directory can be used."""
        ...


class SystemPlatformEnvironment:
    """Production read-only platform and runtime capability probes."""

    def __init__(
        self,
        system: str = sys.platform,
        version: Tuple[int, int, int] = SYSTEM_PYTHON_VERSION,
        os_release_paths: Tuple[Path, ...] = DEFAULT_OS_RELEASE_PATHS,
        temporary_root: Optional[Path] = None,
    ) -> None:
        self._system = system
        self._version = version
        self._os_release_paths = os_release_paths
        self._temporary_root = temporary_root

    def system_name(self) -> str:
        """Return the active Python runtime platform identifier."""
        return self._system

    def python_version(self) -> Tuple[int, int, int]:
        """Return the active Python runtime version."""
        return self._version

    def os_release(self) -> Optional[str]:
        """Read the preferred available Linux os-release file."""
        if self._system != "linux":
            return None
        for path in self._os_release_paths:
            try:
                return path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
        return None

    def temporary_directory_available(self) -> bool:
        """Probe private temporary storage and clean it automatically."""
        root = str(self._temporary_root) if self._temporary_root is not None else None
        try:
            with tempfile.TemporaryDirectory(
                prefix="sdd-tdd-platform-",
                dir=root,
            ) as directory:
                probe = Path(directory) / "probe"
                probe.write_text("available", encoding="utf-8")
                return probe.read_text(encoding="utf-8") == "available"
        except OSError:
            return False


@dataclass(frozen=True)
class PlatformDiagnostic:
    """Sanitized host identity and runtime readiness information."""

    os_family: str
    distribution_id: str
    distribution_version: str
    platform_support: str
    python_version: Tuple[int, int, int]
    python_status: str
    temporary_directory_status: str
    readiness: str


class PlatformDoctor:
    """Diagnose one injected platform environment without mutation."""

    def __init__(self, environment: PlatformEnvironment) -> None:
        self._environment = environment

    def diagnose(self) -> PlatformDiagnostic:
        """Return deterministic host support and readiness classification."""
        system = self._environment.system_name()
        python_version = self._environment.python_version()
        temporary_status = (
            "available"
            if self._environment.temporary_directory_available()
            else "unavailable"
        )
        family, distribution_id, distribution_version, support = (
            self._platform_identity(system)
        )
        python_status = (
            "supported"
            if python_version[:2] >= MINIMUM_PYTHON_VERSION
            else "unsupported"
        )
        readiness = _readiness(support, python_status, temporary_status)
        return PlatformDiagnostic(
            os_family=family,
            distribution_id=distribution_id,
            distribution_version=distribution_version,
            platform_support=support,
            python_version=python_version,
            python_status=python_status,
            temporary_directory_status=temporary_status,
            readiness=readiness,
        )

    def _platform_identity(self, system: str) -> Tuple[str, str, str, str]:
        if system == "darwin":
            return "macos", "not-applicable", "", "supported"
        if system != "linux":
            family = system if system and system.isprintable() else "unknown"
            return family, "unknown", "", "unsupported"
        release = parse_os_release(self._environment.os_release() or "")
        distribution_id = release.get("ID", "unknown")
        distribution_version = release.get("VERSION_ID", "unknown")
        support = (
            "supported-target"
            if distribution_id == "linuxmint"
            else "compatible-untested"
        )
        return "linux", distribution_id, distribution_version, support


def parse_os_release(content: str) -> Dict[str, str]:
    """Parse safe scalar os-release assignments without variable expansion."""
    values: Dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition("=")
        if not separator or OS_RELEASE_KEY.fullmatch(key) is None or key in values:
            raise PlatformContractError("Invalid os-release data")
        try:
            tokens = shlex.split(raw_value, comments=False, posix=True)
        except ValueError as error:
            raise PlatformContractError("Invalid os-release data") from error
        if len(tokens) != 1 or not tokens[0] or not tokens[0].isprintable():
            raise PlatformContractError("Invalid os-release data")
        values[key] = tokens[0]
    return {key: values[key] for key in ("ID", "VERSION_ID") if key in values}


def _readiness(
    platform_support: str,
    python_status: str,
    temporary_status: str,
) -> str:
    if platform_support == "unsupported":
        return "unsupported"
    if python_status != "supported" or temporary_status != "available":
        return "degraded"
    if platform_support == "compatible-untested":
        return "review-required"
    return "ready"


def render_platform_diagnostic(diagnostic: PlatformDiagnostic) -> str:
    """Render a deterministic platform diagnostic without host secrets."""
    distribution = diagnostic.distribution_id
    if diagnostic.distribution_version:
        distribution += f" {diagnostic.distribution_version}"
    python_version = ".".join(str(item) for item in diagnostic.python_version)
    return (
        f"Operating system: {diagnostic.os_family}\n"
        f"Distribution: {distribution}\n"
        f"Platform support: {diagnostic.platform_support}\n"
        f"Python: {python_version} ({diagnostic.python_status})\n"
        f"Temporary directory: {diagnostic.temporary_directory_status}\n"
        f"Readiness: {diagnostic.readiness}\n"
    )
