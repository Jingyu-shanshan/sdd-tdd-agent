import math
from typing import Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    JsonCommandRequirementAnalyzer,
    ProcessResult,
    RequirementAnalyzerError,
)
from sdd_tdd_agent.requirement_analysis import RequirementAnalysisRequest


class ResultRunner:
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


def _adapter(result: ProcessResult) -> JsonCommandRequirementAnalyzer:
    return JsonCommandRequirementAnalyzer(
        config=CommandAnalyzerConfig(command=("bridge",), timeout_seconds=10.0),
        runner=ResultRunner(result),
    )


def test_should_report_exit_code_without_leaking_process_content() -> None:
    adapter = _adapter(
        ProcessResult(
            returncode=17,
            stdout="SECRET-STDOUT",
            stderr="SECRET-STDERR",
        )
    )

    with pytest.raises(RequirementAnalyzerError) as captured:
        adapter.analyze(_request())

    message = str(captured.value)
    assert message == "Analyzer command failed with exit code 17"
    assert "SECRET" not in message
    assert "sensitive" not in message


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("not-json", "Analyzer returned invalid JSON"),
        ("[]", "Analyzer response must be a JSON object"),
        ("{}", "Analyzer response keys do not match schema"),
        (
            """{
              "summary": 42,
              "user_stories": [],
              "functional_requirements": [],
              "non_functional_requirements": [],
              "impact_analysis": [],
              "open_questions": []
            }""",
            "Analyzer field has invalid type: summary",
        ),
        (
            """{
              "summary": "summary",
              "user_stories": [1],
              "functional_requirements": [],
              "non_functional_requirements": [],
              "impact_analysis": [],
              "open_questions": []
            }""",
            "Analyzer field has invalid type: user_stories",
        ),
    ],
)
def test_should_reject_invalid_response_schema(stdout: str, message: str) -> None:
    adapter = _adapter(ProcessResult(returncode=0, stdout=stdout, stderr="SECRET"))

    with pytest.raises(RequirementAnalyzerError, match=message):
        adapter.analyze(_request())


@pytest.mark.parametrize("timeout", [0.0, -1.0, math.inf, math.nan])
def test_should_reject_non_positive_or_non_finite_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        CommandAnalyzerConfig(command=("bridge",), timeout_seconds=timeout)


def test_should_reject_empty_command() -> None:
    with pytest.raises(ValueError, match="non-empty arguments"):
        CommandAnalyzerConfig(command=(), timeout_seconds=10.0)
