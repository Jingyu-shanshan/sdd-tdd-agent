import json
from pathlib import Path

import pytest

from sdd_tdd_agent.task_review import load_active_task_review


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
                "state": "TASK_REVIEW",
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


def test_should_report_missing_project_as_safe_task_review_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Unable to load active Session"):
        load_active_task_review(tmp_path)


def test_should_report_malformed_state_as_safe_task_review_error(
    tmp_path: Path,
) -> None:
    session = _create_active_state(tmp_path)
    (session / "state.json").write_text("{", encoding="utf-8")
    (session / "tasks.md").write_text("# Task Breakdown\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Session state is not valid JSON"):
        load_active_task_review(tmp_path)


def test_should_report_missing_tasks_as_safe_review_error(tmp_path: Path) -> None:
    _create_active_state(tmp_path)

    with pytest.raises(ValueError, match="task review files are missing"):
        load_active_task_review(tmp_path)
