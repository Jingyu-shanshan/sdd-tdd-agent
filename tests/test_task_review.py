import io
import json
from pathlib import Path
from typing import Dict, Union

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.task_review import (
    approve_active_tasks,
    load_active_task_review,
    reject_active_tasks,
)


JsonValue = Union[None, bool, int, float, str, list[object], Dict[str, object]]


def _create_review_workspace(
    root: Path,
    *,
    state: JsonValue = None,
    tasks: str = "# Task Breakdown\n\n## Summary\n\nReady for review.\n",
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(tasks, encoding="utf-8")
    initial_state: JsonValue = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "TASK_REVIEW",
            "current_task": None,
            "current_cycle": 0,
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
        }
    (session / "state.json").write_text(
        json.dumps(initial_state),
        encoding="utf-8",
    )
    return session


def test_should_load_active_tasks_for_human_review(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    review = load_active_task_review(tmp_path)

    assert review.session_id == "feature-1"
    assert review.state == "TASK_REVIEW"
    assert review.tasks == (session / "tasks.md").read_text(encoding="utf-8")
    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_approve_tasks_and_preserve_session_state(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = approve_active_tasks(tmp_path)

    assert decision.session_id == "feature-1"
    assert decision.decision == "approved"
    assert decision.previous_state == "TASK_REVIEW"
    assert decision.next_state == "TEST_GENERATION"
    assert decision.reason is None
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": "feature-1",
        "kind": "feature",
        "state": "TEST_GENERATION",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }


def test_should_reject_tasks_with_normalized_reason(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = reject_active_tasks(tmp_path, "  Split the CLI task.  ")

    assert decision.decision == "rejected"
    assert decision.next_state == "TASK_BREAKDOWN"
    assert decision.reason == "Split the CLI task."
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "TASK_BREAKDOWN"
    assert state["task_review"] == {
        "decision": "rejected",
        "reason": "Split the CLI task.",
    }


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (
            {
                "session_id": "feature-1",
                "state": "TASK_BREAKDOWN",
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
            },
            "requires TASK_REVIEW",
        ),
        (
            {
                "session_id": "another-session",
                "state": "TASK_REVIEW",
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
            },
            "does not match",
        ),
        (
            {
                "session_id": "feature-1",
                "state": "TASK_REVIEW",
                "design_review": {"decision": "approved"},
            },
            "approved requirements",
        ),
        (
            {
                "session_id": "feature-1",
                "state": "TASK_REVIEW",
                "requirement_review": {"decision": "approved"},
            },
            "approved design",
        ),
        (["not", "an", "object"], "JSON object"),
    ],
)
def test_should_reject_invalid_task_review_without_mutation(
    tmp_path: Path,
    state: JsonValue,
    message: str,
) -> None:
    session = _create_review_workspace(tmp_path, state=state)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        approve_active_tasks(tmp_path)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_task_reason_without_mutation(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="reason must not be empty"):
        reject_active_tasks(tmp_path, "   ")

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_tasks(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path, tasks=" \n")

    with pytest.raises(ValueError, match="must not be empty"):
        load_active_task_review(tmp_path)


def test_should_reject_non_generated_tasks(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path, tasks="# Handwritten Tasks\n")

    with pytest.raises(ValueError, match="requires generated tasks"):
        load_active_task_review(tmp_path)


def test_should_reject_missing_active_session_for_task_review(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no active Session"):
        load_active_task_review(tmp_path)


def test_should_show_active_tasks_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["tasks", "show"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (session / "tasks.md").read_text(encoding="utf-8")


def test_should_approve_active_tasks_from_cli(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["tasks", "approve"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == "Tasks approved: feature-1 (TEST_GENERATION)\n"


def test_should_reject_active_tasks_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["tasks", "reject", "Split", "the", "CLI", "task"],
        out=output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == "Tasks rejected: feature-1 (TASK_BREAKDOWN)\n"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["task_review"]["reason"] == "Split the CLI task"


def test_should_report_task_review_error_to_stderr(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path)
    errors = io.StringIO()

    exit_code = main(["tasks", "reject"], root=tmp_path, err=errors)

    assert exit_code == 2
    assert errors.getvalue() == "Error: Task rejection reason must not be empty\n"
