import json
from pathlib import Path

import pytest

from sdd_tdd_agent.requirement_review import load_active_requirement_review


def _create_active_session(root: Path, state_content: str) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(state_content, encoding="utf-8")
    return session


def test_should_report_missing_project_as_safe_review_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unable to load active Session"):
        load_active_requirement_review(tmp_path)


def test_should_report_malformed_state_as_safe_review_error(tmp_path: Path) -> None:
    session = _create_active_session(tmp_path, "{")
    (session / "requirement.md").write_text("Ready.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Session state is not valid JSON"):
        load_active_requirement_review(tmp_path)


def test_should_report_missing_requirement_as_safe_review_error(tmp_path: Path) -> None:
    _create_active_session(
        tmp_path,
        json.dumps(
            {
                "session_id": "feature-1",
                "state": "REQUIREMENT_REVIEW",
            }
        ),
    )

    with pytest.raises(ValueError, match="review files are missing"):
        load_active_requirement_review(tmp_path)
