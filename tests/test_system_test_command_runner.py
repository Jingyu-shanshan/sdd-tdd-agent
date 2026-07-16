import sys
from pathlib import Path

import pytest

from sdd_tdd_agent.red_execution import RedExecutionError, SystemTestCommandRunner


def test_should_execute_test_command_without_shell_in_project_root(
    tmp_path: Path,
) -> None:
    runner = SystemTestCommandRunner()
    script = "from pathlib import Path; print(Path.cwd().name)"

    result = runner.run((sys.executable, "-c", script), tmp_path, 5.0)

    assert result.returncode == 0
    assert result.stdout == f"{tmp_path.name}\n"
    assert result.stderr == ""


def test_should_translate_test_timeout_without_command_content(tmp_path: Path) -> None:
    runner = SystemTestCommandRunner()

    with pytest.raises(RedExecutionError) as captured:
        runner.run(
            (sys.executable, "-c", "import time; time.sleep(1)", "SECRET"),
            tmp_path,
            0.01,
        )

    assert str(captured.value) == "Test command timed out"
    assert "SECRET" not in str(captured.value)


def test_should_translate_start_failure_without_command_content(tmp_path: Path) -> None:
    runner = SystemTestCommandRunner()

    with pytest.raises(RedExecutionError) as captured:
        runner.run(("missing-SECRET-test-command",), tmp_path, 5.0)

    assert str(captured.value) == "Test command could not be started"
    assert "SECRET" not in str(captured.value)
