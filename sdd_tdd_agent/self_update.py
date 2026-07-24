import json
import logging
import os
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable, Optional, TextIO, Tuple
from urllib.request import Request, urlopen

from sdd_tdd_agent.model_adapter import ProcessRunner, RequirementAnalyzerError


PACKAGE_NAME = "sdd-tdd-agent"
PROJECT_METADATA_URL = (
    "https://raw.githubusercontent.com/Jingyu-shanshan/"
    "sdd-tdd-agent/main/pyproject.toml"
)
UPDATE_COMMAND = (
    "uv",
    "tool",
    "install",
    "--force",
    "git+https://github.com/Jingyu-shanshan/sdd-tdd-agent.git",
)
UPDATE_TIMEOUT_SECONDS = 300.0
CHECK_INTERVAL_SECONDS = 86_400
MAX_METADATA_BYTES = 100_000
LOGGER = logging.getLogger(__name__)


class SelfUpdateError(RuntimeError):
    """Safe error raised when the installed tool cannot be updated."""


def _version_tuple(value: str) -> Tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("Version must use X.Y.Z format")
    return int(parts[0]), int(parts[1]), int(parts[2])


def parse_project_version(content: str) -> str:
    """Read one strict version from the remote pyproject project table."""
    in_project = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        key, separator, raw_value = stripped.partition("=")
        if in_project and key.strip() == "version" and separator:
            value = json.loads(raw_value.strip())
            if not isinstance(value, str):
                break
            _version_tuple(value)
            return value
    raise ValueError("Remote project version is missing or invalid")


def _download_metadata(url: str, limit: int) -> bytes:
    request = Request(url, headers={"User-Agent": "wssagent"})
    with urlopen(request, timeout=2) as response:
        return response.read(limit + 1)


def fetch_latest_version(
    downloader: Callable[[str, int], bytes] = _download_metadata,
) -> str:
    """Fetch the bounded public project metadata with a short timeout."""
    content = downloader(PROJECT_METADATA_URL, MAX_METADATA_BYTES)
    if len(content) > MAX_METADATA_BYTES:
        raise ValueError("Remote project metadata is too large")
    return parse_project_version(content.decode("utf-8"))


def _default_cache_path() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    root = Path(configured) if configured else Path.home() / ".cache"
    return root / "wssagent" / "latest-version"


def load_latest_version(
    cache_path: Optional[Path] = None,
    fetcher: Callable[[], str] = fetch_latest_version,
    now: Optional[float] = None,
) -> str:
    """Load a fresh cached version or refresh it from public metadata."""
    path = cache_path or _default_cache_path()
    current_time = time.time() if now is None else now
    try:
        if current_time - path.stat().st_mtime < CHECK_INTERVAL_SECONDS:
            cached = path.read_text(encoding="utf-8").strip()
            _version_tuple(cached)
            return cached
    except (OSError, UnicodeError, ValueError) as error:
        LOGGER.debug("Could not read cached update metadata: %s", error)
    latest = fetcher()
    _version_tuple(latest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(latest + "\n", encoding="utf-8")
    except OSError as error:
        LOGGER.debug("Could not cache update metadata: %s", error)
    return latest


def render_update_notice(current: str, latest: str) -> str:
    """Render a yellow terminal notice only when a newer version exists."""
    if _version_tuple(latest) <= _version_tuple(current):
        return ""
    return (
        f"\033[33mUpdate available: wssagent {current} -> {latest}. "
        "Run 'wssagent update'.\033[0m\n"
    )


def installed_version() -> str:
    """Return the version of the installed wssagent package."""
    return version(PACKAGE_NAME)


def write_update_notice(
    output: TextIO,
    current_loader: Callable[[], str] = installed_version,
    latest_loader: Callable[[], str] = load_latest_version,
) -> None:
    """Write a best-effort interactive update notice."""
    try:
        current = current_loader()
        latest = latest_loader()
    except (OSError, UnicodeError, ValueError, PackageNotFoundError) as error:
        LOGGER.debug("Could not check for a wssagent update: %s", error)
        return
    output.write(render_update_notice(current, latest))


def update_application(runner: ProcessRunner) -> None:
    """Replace the installed uv tool directly from the trusted Git source."""
    try:
        result = runner.run(UPDATE_COMMAND, "", UPDATE_TIMEOUT_SECONDS)
    except RequirementAnalyzerError as error:
        raise SelfUpdateError(
            "wssagent update could not start; verify uv is installed"
        ) from error
    if result.returncode != 0:
        raise SelfUpdateError(
            "wssagent update failed; verify uv is installed and the network is available"
        )
