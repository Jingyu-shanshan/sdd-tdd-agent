import json
from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import prepare_write_test_cycle
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)


def _case(
    test_id: str,
    task_id: str,
    phase: str,
    dependencies: tuple[str, ...] = (),
) -> TestCasePlan:
    return TestCasePlan(
        test_id,
        task_id,
        phase,
        f"Verify {test_id}",
        f"Prove {task_id}.",
        f"tests/test_{task_id.lower()}.py",
        f"test_should_{test_id.lower()}",
        (),
        "Invoke the behavior.",
        ("It works.",),
        dependencies,
    )


def _workspace(root: Path, progress: object = None, cycle: int = 0) -> Path:
    session = root / ".agent" / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: One\n\n## Task T2: Two\n",
        encoding="utf-8",
    )
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan(
        "Two cases.",
        (
            _case("TC1", "T1", "happy_path"),
            _case("TC2", "T2", "boundary", ("TC1",)),
        ),
        (),
        (),
    )
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    state: dict[str, object] = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": None,
        "current_cycle": cycle,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }
    if progress is not None:
        state["tdd_cycle"] = progress
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


def test_should_start_write_test_cycle_when_progress_is_absent(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    prepared = prepare_write_test_cycle(tmp_path, "feature-1")

    assert prepared.test_case.test_id == "TC1"
    assert prepared.cycle_number == 1
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "WRITE_TEST"


def test_should_resume_existing_write_test_cycle_without_mutation(
    tmp_path: Path,
) -> None:
    progress = {
        "current_test": "TC1",
        "phase": "WRITE_TEST",
        "completed_tests": [],
    }
    session = _workspace(tmp_path, progress, cycle=4)
    before = (session / "state.json").read_text(encoding="utf-8")

    prepared = prepare_write_test_cycle(tmp_path, "feature-1")

    assert prepared.test_case.test_id == "TC1"
    assert prepared.cycle_number == 4
    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_start_next_cycle_after_green_prefix(tmp_path: Path) -> None:
    session = _workspace(
        tmp_path,
        {
            "current_test": "TC1",
            "phase": "GREEN",
            "completed_tests": ["TC1"],
        },
        cycle=1,
    )

    prepared = prepare_write_test_cycle(tmp_path, "feature-1")

    assert prepared.test_case.test_id == "TC2"
    assert prepared.cycle_number == 2
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"] == {
        "current_test": "TC2",
        "phase": "WRITE_TEST",
        "completed_tests": ["TC1"],
    }


@pytest.mark.parametrize("phase", ["RED", "IMPLEMENT"])
def test_should_reject_non_writing_active_cycle_without_mutation(
    tmp_path: Path,
    phase: str,
) -> None:
    session = _workspace(
        tmp_path,
        {"current_test": "TC1", "phase": phase, "completed_tests": []},
        cycle=1,
    )
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="already active"):
        prepare_write_test_cycle(tmp_path, "feature-1")

    assert (session / "state.json").read_text(encoding="utf-8") == before
