import json
from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import (
    BlindDevelopmentContext,
    SourceSnapshot,
    select_next_test_case,
    start_next_tdd_cycle,
)
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
        test_id=test_id,
        task_id=task_id,
        phase=phase,
        title=f"Verify {test_id}",
        objective=f"Prove {task_id}.",
        test_file=f"tests/test_{task_id.lower()}.py",
        test_name=f"test_should_{test_id.lower()}",
        preconditions=("A fixture exists.",),
        action="Invoke the behavior.",
        expected_outcomes=("The expected result is returned.",),
        dependencies=dependencies,
    )


def _render_plan() -> str:
    request = TestGenerationRequest(
        "v1", "Prompt", "Req", "Design", "Tasks", "P", "A", "C"
    )
    plan = GeneratedTestPlan(
        "Two cases.",
        (
            _case("TC1", "T1", "happy_path"),
            _case("TC2", "T2", "boundary", ("TC1",)),
        ),
        (),
        (),
    )
    return render_test_plan(request, plan)


def _workspace(root: Path, tdd_cycle: object = None) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Service\n\n## Task T2: CLI\n",
        encoding="utf-8",
    )
    (session / "test-plan.md").write_text(_render_plan(), encoding="utf-8")
    state: dict[str, object] = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }
    if tdd_cycle is not None:
        state["tdd_cycle"] = tdd_cycle
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


def test_should_select_first_incomplete_test_from_generated_plan(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)

    case = select_next_test_case(tmp_path, "feature-1")

    assert case is not None
    assert case.test_id == "TC1"
    assert case.task_id == "T1"
    assert case.preconditions == ("A fixture exists.",)


def test_should_select_next_case_after_green_completion(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        {"current_test": "TC1", "phase": "GREEN", "completed_tests": ["TC1"]},
    )

    case = select_next_test_case(tmp_path, "feature-1")

    assert case is not None
    assert case.test_id == "TC2"
    assert case.dependencies == ("TC1",)


def test_should_return_none_when_every_test_is_complete(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        {
            "current_test": "TC2",
            "phase": "GREEN",
            "completed_tests": ["TC1", "TC2"],
        },
    )

    assert select_next_test_case(tmp_path, "feature-1") is None


def test_should_start_next_cycle_atomically(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    started = start_next_tdd_cycle(tmp_path, "feature-1")

    assert started.test_case.test_id == "TC1"
    assert started.cycle_number == 1
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "IMPLEMENTATION"
    assert state["current_task"] == "T1"
    assert state["current_cycle"] == 1
    assert state["tdd_cycle"] == {
        "current_test": "TC1",
        "phase": "WRITE_TEST",
        "completed_tests": [],
    }


def test_should_preserve_completed_tests_when_starting_next_cycle(
    tmp_path: Path,
) -> None:
    session = _workspace(
        tmp_path,
        {"current_test": "TC1", "phase": "GREEN", "completed_tests": ["TC1"]},
    )

    started = start_next_tdd_cycle(tmp_path, "feature-1")

    assert started.test_case.test_id == "TC2"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["completed_tests"] == ["TC1"]
    assert state["tdd_cycle"]["phase"] == "WRITE_TEST"


@pytest.mark.parametrize(
    "progress",
    [
        {"current_test": "TC1", "phase": "WRITE_TEST", "completed_tests": []},
        {"current_test": "UNKNOWN", "phase": "GREEN", "completed_tests": []},
        {"current_test": "TC1", "phase": "GREEN", "completed_tests": ["UNKNOWN"]},
        {"current_test": "TC1", "phase": "GREEN", "completed_tests": "TC1"},
    ],
)
def test_should_reject_invalid_or_active_progress_without_mutation(
    tmp_path: Path,
    progress: object,
) -> None:
    session = _workspace(tmp_path, progress)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        start_next_tdd_cycle(tmp_path, "feature-1")

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_wrong_workflow_state_before_mutation(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["state"] = "TEST_GENERATION"
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="IMPLEMENTATION"):
        start_next_tdd_cycle(tmp_path, "feature-1")

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_build_context_without_future_or_specification_content() -> None:
    current = _case("TC1", "T1", "happy_path")
    context = BlindDevelopmentContext(
        current_test=current,
        production_sources=(SourceSnapshot("src/export.py", "def export(): ...\n"),),
        compile_output="Compilation succeeded.",
        test_output="TC1 failed.",
    )

    assert context.current_test == current
    assert context.production_sources[0].path == "src/export.py"
    assert context.compile_output == "Compilation succeeded."
    assert context.test_output == "TC1 failed."
    assert not hasattr(context, "requirement")
    assert not hasattr(context, "design")
    assert not hasattr(context, "tasks")
    assert not hasattr(context, "future_tests")
