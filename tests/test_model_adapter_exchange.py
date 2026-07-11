import json
from typing import Optional, Tuple

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    JsonCommandRequirementAnalyzer,
    ProcessResult,
)
from sdd_tdd_agent.requirement_analysis import RequirementAnalysisRequest


class FakeProcessRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None
        self.timeout_seconds: Optional[float] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        self.timeout_seconds = timeout_seconds
        return self.result


def test_should_exchange_typed_json_through_injected_runner() -> None:
    runner = FakeProcessRunner(
        ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {
                    "summary": "Export reports as PDF.",
                    "user_stories": ["A user can export a report."],
                    "functional_requirements": ["Provide a PDF export action."],
                    "non_functional_requirements": ["Preserve data accuracy."],
                    "impact_analysis": ["Report delivery may be affected."],
                    "open_questions": ["Which layouts are supported?"],
                }
            ),
            stderr="",
        )
    )
    adapter = JsonCommandRequirementAnalyzer(
        config=CommandAnalyzerConfig(
            command=("model-bridge", "analyze"),
            timeout_seconds=45.0,
        ),
        runner=runner,
    )
    request = RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="Analyze safely.",
        user_request="Support PDF export",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )

    analysis = adapter.analyze(request)

    assert runner.command == ("model-bridge", "analyze")
    assert runner.timeout_seconds == 45.0
    assert runner.stdin is not None
    assert json.loads(runner.stdin) == {
        "prompt_version": "v1",
        "prompt": "Analyze safely.",
        "user_request": "Support PDF export",
        "project_metadata": "name: reports",
        "architecture": "# Architecture",
        "conventions": "# Conventions",
    }
    assert analysis.summary == "Export reports as PDF."
    assert analysis.functional_requirements == ("Provide a PDF export action.",)
