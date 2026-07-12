import json
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.model_adapter import (
    CodexExecRequirementAnalyzer,
    CommandAnalyzerConfig,
    ProcessResult,
)
from sdd_tdd_agent.requirement_analysis import RequirementAnalysisRequest


class RecordingCodexRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None
        self.timeout_seconds: Optional[float] = None
        self.schema: Optional[object] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        self.timeout_seconds = timeout_seconds
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        output_path.write_text(
            json.dumps(
                {
                    "summary": "Add PDF export.",
                    "user_stories": ["Export a report as PDF."],
                    "functional_requirements": ["Provide PDF output."],
                    "non_functional_requirements": [],
                    "impact_analysis": ["Report delivery changes."],
                    "open_questions": [],
                }
            ),
            encoding="utf-8",
        )
        return ProcessResult(returncode=0, stdout="progress", stderr="")


def test_should_exchange_requirement_analysis_through_codex_exec(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner()
    analyzer = CodexExecRequirementAnalyzer(
        config=CommandAnalyzerConfig(command=("codex",), timeout_seconds=120),
        runner=runner,
        workspace=tmp_path,
    )
    request = RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="Return structured requirements.",
        user_request="Support PDF export",
        project_metadata="name: example",
        architecture="# Architecture",
        conventions="# Conventions",
    )

    analysis = analyzer.analyze(request)

    assert runner.command is not None
    assert runner.command[0:2] == ("codex", "exec")
    assert "--ephemeral" in runner.command
    assert runner.command[runner.command.index("--sandbox") + 1] == "read-only"
    assert runner.command[runner.command.index("--color") + 1] == "never"
    assert runner.command[runner.command.index("--cd") + 1] == str(tmp_path)
    assert runner.command[-1] == "-"
    assert runner.timeout_seconds == 120
    assert runner.schema == {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "user_stories": {"type": "array", "items": {"type": "string"}},
            "functional_requirements": {
                "type": "array",
                "items": {"type": "string"},
            },
            "non_functional_requirements": {
                "type": "array",
                "items": {"type": "string"},
            },
            "impact_analysis": {
                "type": "array",
                "items": {"type": "string"},
            },
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "summary",
            "user_stories",
            "functional_requirements",
            "non_functional_requirements",
            "impact_analysis",
            "open_questions",
        ],
        "additionalProperties": False,
    }
    assert runner.stdin is not None
    assert json.loads(runner.stdin)["user_request"] == "Support PDF export"
    assert analysis.summary == "Add PDF export."
