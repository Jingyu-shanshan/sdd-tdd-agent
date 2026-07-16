from pathlib import Path

import pytest

from sdd_tdd_agent.execution_config import (
    TestExecutionConfigurationError,
    load_full_test_suite_timeout,
)
from sdd_tdd_agent.project_init import initialize_project


def _config(root: Path, content: str) -> None:
    workspace = root / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(content, encoding="utf-8")


def test_should_load_explicit_full_suite_timeout(tmp_path: Path) -> None:
    _config(tmp_path, "full_test_suite_timeout_seconds: 90.5\n")

    assert load_full_test_suite_timeout(tmp_path) == 90.5


@pytest.mark.parametrize(
    "content",
    [
        "test_command_timeout_seconds: 10\n",
        "full_test_suite_timeout_seconds:\n",
        "full_test_suite_timeout_seconds: nope\n",
        "full_test_suite_timeout_seconds: nan\n",
        "full_test_suite_timeout_seconds: inf\n",
        "full_test_suite_timeout_seconds: 0\n",
        "full_test_suite_timeout_seconds: -1\n",
        "full_test_suite_timeout_seconds: 5\nfull_test_suite_timeout_seconds: 6\n",
    ],
)
def test_should_reject_invalid_full_suite_timeout(
    tmp_path: Path,
    content: str,
) -> None:
    _config(tmp_path, content)

    with pytest.raises(TestExecutionConfigurationError):
        load_full_test_suite_timeout(tmp_path)


def test_should_bootstrap_explicit_full_suite_timeout(tmp_path: Path) -> None:
    initialize_project(tmp_path)

    content = (tmp_path / ".agent" / "config.yml").read_text(encoding="utf-8")
    assert "full_test_suite_timeout_seconds: 900\n" in content
