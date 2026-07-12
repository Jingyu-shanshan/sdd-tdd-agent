from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CodexExecRequirementAnalyzer,
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
)
from sdd_tdd_agent.requirement_analysis import RequirementAnalysisRequest


class FixedCodexRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return self.result


def _request() -> RequirementAnalysisRequest:
    return RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="sensitive prompt",
        user_request="sensitive request",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )


def test_should_reject_codex_command_with_extra_tokens(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecRequirementAnalyzer(
            config=CommandAnalyzerConfig(
                command=("codex", "--unexpected"),
                timeout_seconds=10,
            ),
            runner=FixedCodexRunner(ProcessResult(0, "", "")),
            workspace=tmp_path,
        )


def test_should_report_codex_exit_code_without_process_content(
    tmp_path: Path,
) -> None:
    analyzer = CodexExecRequirementAnalyzer(
        config=CommandAnalyzerConfig(command=("codex",), timeout_seconds=10),
        runner=FixedCodexRunner(ProcessResult(23, "SECRET-STDOUT", "SECRET-STDERR")),
        workspace=tmp_path,
    )

    with pytest.raises(RequirementAnalyzerError) as captured:
        analyzer.analyze(_request())

    assert str(captured.value) == "Codex command failed with exit code 23"
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


def test_should_reject_missing_codex_output(tmp_path: Path) -> None:
    analyzer = CodexExecRequirementAnalyzer(
        config=CommandAnalyzerConfig(command=("codex",), timeout_seconds=10),
        runner=FixedCodexRunner(ProcessResult(0, "", "")),
        workspace=tmp_path,
    )

    with pytest.raises(
        RequirementAnalyzerError,
        match="Codex analyzer output could not be read",
    ):
        analyzer.analyze(_request())
