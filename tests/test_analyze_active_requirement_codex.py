import json
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.analyze_command import analyze_active_requirement
from sdd_tdd_agent.model_adapter import ProcessResult


class CodexAnalysisRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "summary": "Export reports as PDFs.",
                    "user_stories": ["A user can export a report."],
                    "functional_requirements": ["Provide an export action."],
                    "non_functional_requirements": [],
                    "impact_analysis": [],
                    "open_questions": [],
                }
            ),
            encoding="utf-8",
        )
        return ProcessResult(returncode=0, stdout="", stderr="")


def test_should_analyze_active_session_through_codex_protocol(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 300
""",
        encoding="utf-8",
    )
    (workspace / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (workspace / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    (session / "requirement.md").write_text(
        "# Requirement\n\n## User request\n\nSupport PDF export\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "ANALYSIS",
                "current_task": None,
                "current_cycle": 0,
            }
        ),
        encoding="utf-8",
    )
    runner = CodexAnalysisRunner()

    run = analyze_active_requirement(tmp_path, runner)

    assert runner.command is not None
    assert runner.command[0:2] == ("codex", "exec")
    assert run.next_state == "REQUIREMENT_REVIEW"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "REQUIREMENT_REVIEW"
