import io
import json
from pathlib import Path
from typing import Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult


class CliAnalysisRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(
            returncode=0,
            stdout=json.dumps(
                {
                    "summary": "Export reports as PDFs.",
                    "user_stories": ["A user can export a report."],
                    "functional_requirements": ["Provide an export action."],
                    "non_functional_requirements": [],
                    "impact_analysis": [],
                    "open_questions": [],
                }
            ),
            stderr="",
        )


def test_should_run_active_analysis_from_cli(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_command:
  - "bridge"
requirement_analyzer_timeout_seconds: 30
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
    output = io.StringIO()

    exit_code = main(
        ["analyze"],
        out=output,
        root=tmp_path,
        runner=CliAnalysisRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Requirement analysis ready for review: feature-1 (REQUIREMENT_REVIEW)\n"
    )
