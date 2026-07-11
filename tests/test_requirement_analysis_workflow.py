import json
from pathlib import Path
from typing import Optional

from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysis,
    RequirementAnalysisRequest,
    run_requirement_analysis,
)


class FakeRequirementAnalyzer:
    def __init__(self) -> None:
        self.received_request: Optional[RequirementAnalysisRequest] = None

    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        self.received_request = request
        return RequirementAnalysis(
            summary="Export reports as PDFs.",
            user_stories=("As a user, I can export a report as PDF.",),
            functional_requirements=("Provide a PDF export action.",),
            non_functional_requirements=("Preserve report accuracy.",),
            impact_analysis=("Report delivery may be affected.",),
            open_questions=("Which layouts are supported?",),
        )


def test_should_run_injected_analysis_and_enter_human_review(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
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
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    (workspace / "architecture.md").write_text(
        "# Architecture\n",
        encoding="utf-8",
    )
    (workspace / "conventions.md").write_text(
        "# Conventions\n",
        encoding="utf-8",
    )
    analyzer = FakeRequirementAnalyzer()

    run = run_requirement_analysis(tmp_path, "feature-1", analyzer)

    assert analyzer.received_request is not None
    assert analyzer.received_request.user_request == "Support PDF export"
    assert run.session_id == "feature-1"
    assert run.next_state == "REQUIREMENT_REVIEW"
    assert "## Functional requirements" in (session / "requirement.md").read_text(
        encoding="utf-8"
    )
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "REQUIREMENT_REVIEW"
