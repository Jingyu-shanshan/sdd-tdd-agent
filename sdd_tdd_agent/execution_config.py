import math
from pathlib import Path
from typing import Optional


TIMEOUT_KEY = "test_command_timeout_seconds"
FULL_SUITE_TIMEOUT_KEY = "full_test_suite_timeout_seconds"


class TestExecutionConfigurationError(ValueError):
    """Safe public error for invalid test-command configuration."""

    __test__ = False


def _load_timeout(root: Path, key_name: str, label: str) -> float:
    path = root / ".agent" / "config.yml"
    timeout: Optional[float] = None
    found = False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise TestExecutionConfigurationError(
            "Test command configuration could not be read"
        ) from error
    for line in content.splitlines():
        value = line.strip()
        if not value or value.startswith("#") or line[0].isspace():
            continue
        key, separator, scalar = value.partition(":")
        if key != key_name:
            continue
        if found or not separator or not scalar.strip():
            raise TestExecutionConfigurationError(f"Invalid {label} timeout config")
        found = True
        try:
            timeout = float(scalar.strip())
        except ValueError as error:
            raise TestExecutionConfigurationError(
                f"Invalid {label} timeout config"
            ) from error
    if timeout is None:
        raise TestExecutionConfigurationError(
            f"{label.capitalize()} configuration is incomplete; add "
            f"{key_name} to .agent/config.yml"
        )
    if not math.isfinite(timeout) or timeout <= 0:
        raise TestExecutionConfigurationError(
            f"{label.capitalize()} timeout must be a positive finite number"
        )
    return timeout


def load_test_command_timeout(root: Path) -> float:
    """Load one explicit positive finite current-test timeout."""
    return _load_timeout(root, TIMEOUT_KEY, "test command")


def load_full_test_suite_timeout(root: Path) -> float:
    """Load one explicit positive finite full-suite timeout."""
    return _load_timeout(root, FULL_SUITE_TIMEOUT_KEY, "full test suite")
