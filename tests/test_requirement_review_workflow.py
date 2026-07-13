import json
from pathlib import Path
from typing import Dict, Union

import pytest

from sdd_tdd_agent.requirement_review import (
    approve_active_requirement,
    load_active_requirement_review,
    reject_active_requirement,
)


JsonValue = Union[None, bool, int, float, str, list[object], Dict[str, object]]


def _create_review_workspace(
    root: Path,
    *,
    state: JsonValue = None,
    requirement: str = "# Requirement Analysis\n\nReady for review.\n",
    current_session: str = "feature-1",
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        f"name: reports\ncurrent_session: {current_session}\n",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(requirement, encoding="utf-8")
    initial_state: JsonValue = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "REQUIREMENT_REVIEW",
            "current_task": None,
            "current_cycle": 0,
        }
    (session / "state.json").write_text(
        json.dumps(initial_state),
        encoding="utf-8",
    )
    return session


def test_should_load_active_requirement_for_human_review(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    review = load_active_requirement_review(tmp_path)

    assert review.session_id == "feature-1"
    assert review.state == "REQUIREMENT_REVIEW"
    assert review.requirement == (session / "requirement.md").read_text(
        encoding="utf-8"
    )


def test_should_approve_review_and_preserve_session_state(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = approve_active_requirement(tmp_path)

    assert decision.session_id == "feature-1"
    assert decision.decision == "approved"
    assert decision.previous_state == "REQUIREMENT_REVIEW"
    assert decision.next_state == "DESIGN"
    assert decision.reason is None
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": "feature-1",
        "kind": "feature",
        "state": "DESIGN",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
    }


def test_should_reject_review_with_normalized_reason(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)

    decision = reject_active_requirement(tmp_path, "  Clarify the output format.  ")

    assert decision.decision == "rejected"
    assert decision.next_state == "ANALYSIS"
    assert decision.reason == "Clarify the output format."
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "ANALYSIS"
    assert state["requirement_review"] == {
        "decision": "rejected",
        "reason": "Clarify the output format.",
    }


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ({"session_id": "feature-1", "state": "ANALYSIS"}, "requires"),
        (
            {"session_id": "another-session", "state": "REQUIREMENT_REVIEW"},
            "does not match",
        ),
        (["not", "an", "object"], "JSON object"),
    ],
)
def test_should_reject_invalid_review_state_without_mutation(
    tmp_path: Path,
    state: JsonValue,
    message: str,
) -> None:
    session = _create_review_workspace(tmp_path, state=state)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        approve_active_requirement(tmp_path)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_reason_without_mutation(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="reason must not be empty"):
        reject_active_requirement(tmp_path, "   ")

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_empty_requirement(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path, requirement=" \n")

    with pytest.raises(ValueError, match="must not be empty"):
        load_active_requirement_review(tmp_path)


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no active Session"):
        load_active_requirement_review(tmp_path)
