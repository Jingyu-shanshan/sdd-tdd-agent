import json
from pathlib import Path

import pytest

from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysis,
    RequirementAnalysisRequest,
    run_requirement_analysis,
)


def _create_analysis_session(tmp_path: Path, state: str) -> Path:
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
                "state": state,
                "current_task": None,
                "current_cycle": 0,
            }
        ),
        encoding="utf-8",
    )
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    (workspace / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (workspace / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    return session


class InvalidOutputAnalyzer:
    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        return RequirementAnalysis(
            summary="",
            user_stories=(),
            functional_requirements=(),
            non_functional_requirements=(),
            impact_analysis=(),
            open_questions=(),
        )


class UnexpectedAnalyzer:
    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        raise AssertionError("Analyzer must not run in the wrong state")


def test_should_reject_invalid_analysis_before_mutation(tmp_path: Path) -> None:
    session = _create_analysis_session(tmp_path, "ANALYSIS")
    original_requirement = (session / "requirement.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="summary must not be empty"):
        run_requirement_analysis(tmp_path, "feature-1", InvalidOutputAnalyzer())

    assert (session / "requirement.md").read_text(
        encoding="utf-8"
    ) == original_requirement
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


def test_should_reject_wrong_state_before_analyzer_call(tmp_path: Path) -> None:
    session = _create_analysis_session(tmp_path, "REQUIREMENT_REVIEW")
    original_requirement = (session / "requirement.md").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="requires ANALYSIS state"):
        run_requirement_analysis(tmp_path, "feature-1", UnexpectedAnalyzer())

    assert (session / "requirement.md").read_text(
        encoding="utf-8"
    ) == original_requirement
