import math
from pathlib import Path
from typing import Optional


TIMEOUT_KEY = "test_command_timeout_seconds"


class TestExecutionConfigurationError(ValueError):
    """Safe public error for invalid test-command configuration."""

    __test__ = False


def load_test_command_timeout(root: Path) -> float:
    """Load one explicit positive finite test-command timeout."""
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
        if key != TIMEOUT_KEY:
            continue
        if found or not separator or not scalar.strip():
            raise TestExecutionConfigurationError("Invalid test command timeout config")
        found = True
        try:
            timeout = float(scalar.strip())
        except ValueError as error:
            raise TestExecutionConfigurationError(
                "Invalid test command timeout config"
            ) from error
    if timeout is None:
        raise TestExecutionConfigurationError(
            "Test command configuration is incomplete; add "
            "test_command_timeout_seconds to .agent/config.yml"
        )
    if not math.isfinite(timeout) or timeout <= 0:
        raise TestExecutionConfigurationError(
            "Test command timeout must be a positive finite number"
        )
    return timeout
