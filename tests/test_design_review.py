import io
import json
from pathlib import Path
from typing import Dict, Union

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.design_review import (
    approve_active_design,
    load_active_design_review,
    reject_active_design,
)


JsonValue = Union[None, bool, int, float, str, list[object], Dict[str, object]]


def _create_review_workspace(
    root: Path,
    *,
    state: JsonValue = None,
    design: str = "# Design Proposal\n\n## Overview\n\nReady for review.\n",
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(design, encoding="utf-8")
    initial_state: JsonValue = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "DESIGN_REVIEW",
            "current_task": None,
            "current_cycle": 0,
            "requirement_review": {"decision": "approved"},
        }
    (session / "state.json").write_text(
        json.dumps(initial_state),
        encoding="utf-8",
    )
    return session


def test_should_load_active_design_for_human_review(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    review = load_active_design_review(tmp_path)

    assert review.session_id == "feature-1"
    assert review.state == "DESIGN_REVIEW"
    assert review.design == (session / "design.md").read_text(encoding="utf-8")


def test_should_approve_design_and_preserve_session_state(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = approve_active_design(tmp_path)

    assert decision.session_id == "feature-1"
    assert decision.decision == "approved"
    assert decision.previous_state == "DESIGN_REVIEW"
    assert decision.next_state == "TASK_BREAKDOWN"
    assert decision.reason is None
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": "feature-1",
        "kind": "feature",
        "state": "TASK_BREAKDOWN",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
    }


def test_should_reject_design_with_normalized_reason(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = reject_active_design(tmp_path, "  Clarify the component boundary.  ")

    assert decision.decision == "rejected"
    assert decision.next_state == "DESIGN"
    assert decision.reason == "Clarify the component boundary."
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DESIGN"
    assert state["design_review"] == {
        "decision": "rejected",
        "reason": "Clarify the component boundary.",
    }


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (
            {
                "session_id": "feature-1",
                "state": "DESIGN",
                "requirement_review": {"decision": "approved"},
            },
            "requires DESIGN_REVIEW",
        ),
        (
            {
                "session_id": "another-session",
                "state": "DESIGN_REVIEW",
                "requirement_review": {"decision": "approved"},
            },
            "does not match",
        ),
        (
            {"session_id": "feature-1", "state": "DESIGN_REVIEW"},
            "approved requirements",
        ),
        (["not", "an", "object"], "JSON object"),
    ],
)
def test_should_reject_invalid_design_review_without_mutation(
    tmp_path: Path,
    state: JsonValue,
    message: str,
) -> None:
    session = _create_review_workspace(tmp_path, state=state)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        approve_active_design(tmp_path)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_reason_without_mutation(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="reason must not be empty"):
        reject_active_design(tmp_path, "   ")

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_design(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path, design=" \n")

    with pytest.raises(ValueError, match="must not be empty"):
        load_active_design_review(tmp_path)


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no active Session"):
        load_active_design_review(tmp_path)


def test_should_show_active_design_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["design", "show"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (session / "design.md").read_text(encoding="utf-8")


def test_should_approve_active_design_from_cli(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["design", "approve"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == "Design approved: feature-1 (TASK_BREAKDOWN)\n"


def test_should_reject_active_design_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["design", "reject", "Clarify", "the", "boundary"],
        out=output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == "Design rejected: feature-1 (DESIGN)\n"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["design_review"]["reason"] == "Clarify the boundary"


def test_should_report_design_review_error_to_stderr(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path)
    errors = io.StringIO()

    exit_code = main(["design", "reject"], root=tmp_path, err=errors)

    assert exit_code == 2
    assert errors.getvalue() == "Error: Design rejection reason must not be empty\n"
