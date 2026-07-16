import json
from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import select_next_test_case, start_next_tdd_cycle
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)


def _workspace(root: Path, state: object) -> Path:
    session = root / ".agent" / "sessions" / "feature-1"
    session.mkdir(parents=True)
    case = TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Verify service",
        "Prove service.",
        "tests/test_service.py",
        "test_should_work",
        (),
        "Invoke service.",
        ("It works.",),
        (),
    )
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "M", "A", "C")
    plan = GeneratedTestPlan("Plan", (case,), (), ())
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Service\n",
        encoding="utf-8",
    )
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


def _valid_state() -> dict[str, object]:
    return {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }


def test_should_reject_start_when_all_planned_tests_are_complete(
    tmp_path: Path,
) -> None:
    state = _valid_state()
    state["tdd_cycle"] = {
        "current_test": "TC1",
        "phase": "GREEN",
        "completed_tests": ["TC1"],
    }
    _workspace(tmp_path, state)

    with pytest.raises(ValueError, match="All planned tests are complete"):
        start_next_tdd_cycle(tmp_path, "feature-1")


def test_should_reject_invalid_cycle_number(tmp_path: Path) -> None:
    state = _valid_state()
    state["current_cycle"] = True
    _workspace(tmp_path, state)

    with pytest.raises(ValueError, match="cycle number"):
        start_next_tdd_cycle(tmp_path, "feature-1")


@pytest.mark.parametrize(
    "state",
    [
        ["not", "an", "object"],
        {
            "session_id": "another-session",
            "state": "IMPLEMENTATION",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "IMPLEMENTATION",
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
    ],
)
def test_should_reject_invalid_cycle_state(tmp_path: Path, state: object) -> None:
    _workspace(tmp_path, state)

    with pytest.raises(ValueError):
        select_next_test_case(tmp_path, "feature-1")


def test_should_reject_unsafe_session_identifier(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid Session identifier"):
        select_next_test_case(tmp_path, "../outside")
