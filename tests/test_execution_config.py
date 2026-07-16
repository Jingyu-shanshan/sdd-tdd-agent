from pathlib import Path

import pytest

from sdd_tdd_agent.execution_config import (
    TestExecutionConfigurationError,
    load_test_command_timeout,
)


def _config(root: Path, content: str) -> None:
    workspace = root / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(content, encoding="utf-8")


def test_should_load_positive_finite_test_command_timeout(tmp_path: Path) -> None:
    _config(tmp_path, "max_iterations: 20\ntest_command_timeout_seconds: 45.5\n")

    assert load_test_command_timeout(tmp_path) == 45.5


def test_should_translate_missing_config_to_safe_error(tmp_path: Path) -> None:
    with pytest.raises(TestExecutionConfigurationError, match="could not be read"):
        load_test_command_timeout(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        "max_iterations: 20\n",
        "test_command_timeout_seconds:\n",
        "test_command_timeout_seconds: nope\n",
        "test_command_timeout_seconds: nan\n",
        "test_command_timeout_seconds: inf\n",
        "test_command_timeout_seconds: 0\n",
        "test_command_timeout_seconds: -1\n",
        "test_command_timeout_seconds: 5\ntest_command_timeout_seconds: 6\n",
    ],
)
def test_should_reject_invalid_or_missing_test_command_timeout(
    tmp_path: Path,
    content: str,
) -> None:
    _config(tmp_path, content)

    with pytest.raises(TestExecutionConfigurationError):
        load_test_command_timeout(tmp_path)
