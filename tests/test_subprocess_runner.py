import sys

import pytest

from sdd_tdd_agent.model_adapter import RequirementAnalyzerError, SubprocessRunner


def test_should_execute_tokenized_command_without_shell() -> None:
    runner = SubprocessRunner()
    script = "import sys; sys.stdout.write(sys.stdin.read().upper())"

    result = runner.run(
        command=(sys.executable, "-c", script),
        stdin="hello adapter",
        timeout_seconds=5.0,
    )

    assert result.returncode == 0
    assert result.stdout == "HELLO ADAPTER"
    assert result.stderr == ""


def test_should_translate_timeout_without_process_content() -> None:
    runner = SubprocessRunner()
    script = "import time; time.sleep(1)"

    with pytest.raises(RequirementAnalyzerError) as captured:
        runner.run(
            command=(sys.executable, "-c", script),
            stdin="SECRET-STDIN",
            timeout_seconds=0.01,
        )

    assert str(captured.value) == "Analyzer command timed out"
    assert "SECRET" not in str(captured.value)
