from pathlib import Path

import pytest

from sdd_tdd_agent.model_adapter import RequirementAnalyzerError, SubprocessRunner


def test_should_translate_process_start_failure_without_path_leak(
    tmp_path: Path,
) -> None:
    missing_executable = tmp_path / "SECRET-missing-executable"
    runner = SubprocessRunner()

    with pytest.raises(RequirementAnalyzerError) as captured:
        runner.run(
            command=(str(missing_executable),),
            stdin="SECRET-STDIN",
            timeout_seconds=1.0,
        )

    assert str(captured.value) == "Analyzer command could not be started"
    assert "SECRET" not in str(captured.value)
