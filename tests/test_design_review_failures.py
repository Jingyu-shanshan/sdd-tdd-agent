import json
from pathlib import Path

import pytest

from sdd_tdd_agent.design_review import load_active_design_review


def _create_active_state(root: Path) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "state": "DESIGN_REVIEW",
                "requirement_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


def test_should_report_missing_project_as_safe_design_review_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Unable to load active Session"):
        load_active_design_review(tmp_path)


def test_should_report_malformed_state_as_safe_design_review_error(
    tmp_path: Path,
) -> None:
    session = _create_active_state(tmp_path)
    (session / "state.json").write_text("{", encoding="utf-8")
    (session / "design.md").write_text("# Design Proposal\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Session state is not valid JSON"):
        load_active_design_review(tmp_path)


def test_should_report_missing_design_as_safe_review_error(tmp_path: Path) -> None:
    _create_active_state(tmp_path)

    with pytest.raises(ValueError, match="design review files are missing"):
        load_active_design_review(tmp_path)


def test_should_reject_non_generated_design(tmp_path: Path) -> None:
    session = _create_active_state(tmp_path)
    (session / "design.md").write_text("# Handwritten Notes\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires a generated design"):
        load_active_design_review(tmp_path)
