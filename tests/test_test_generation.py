import json
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    load_test_generation_request,
    render_test_plan,
    run_test_generation,
)


def _case(
    test_id: str,
    task_id: str,
    phase: str,
    dependencies: tuple[str, ...] = (),
    test_file: str = "tests/test_export.py",
) -> TestCasePlan:
    return TestCasePlan(
        test_id=test_id,
        task_id=task_id,
        phase=phase,
        title=f"Verify {test_id}",
        objective=f"Prove {task_id} behavior.",
        test_file=test_file,
        test_name=f"test_should_{test_id.lower()}",
        preconditions=(),
        action=f"Invoke behavior for {task_id}.",
        expected_outcomes=(f"{task_id} returns the expected result.",),
        dependencies=dependencies,
    )


def _plan() -> GeneratedTestPlan:
    return GeneratedTestPlan(
        summary="Verify PDF export in two incremental tests.",
        cases=(
            _case("TC1", "T1", "happy_path"),
            _case("TC2", "T2", "boundary", dependencies=("TC1",)),
        ),
        risks=("PDF rendering may vary by platform.",),
        open_questions=("Which page size is required?",),
    )


def _task_artifact() -> str:
    return """\
# Task Breakdown

## Summary

Implement PDF export.

## Task T1: Export service

### Objective

Implement the service.

## Task T2: CLI integration

### Objective

Connect the service.
"""


def _create_test_workspace(
    root: Path,
    *,
    state: object = None,
    test_plan: str = "# Test Plan\n\nPending.\n",
    tasks: Optional[str] = None,
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    (workspace / "architecture.md").write_text(
        "# Architecture\n\nThin CLI.\n",
        encoding="utf-8",
    )
    (workspace / "conventions.md").write_text(
        "# Conventions\n\nUse incremental TDD.\n",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\n## Summary\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\n## Overview\n\nUse an export service.\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        _task_artifact() if tasks is None else tasks,
        encoding="utf-8",
    )
    (session / "test-plan.md").write_text(test_plan, encoding="utf-8")
    initial_state = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "TEST_GENERATION",
            "current_task": None,
            "current_cycle": 0,
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        }
    (session / "state.json").write_text(
        json.dumps(initial_state),
        encoding="utf-8",
    )
    return session


class FakeTestPlanGenerator:
    def __init__(self, plan: object = None) -> None:
        self.received_request: Optional[TestGenerationRequest] = None
        self._plan = _plan() if plan is None else plan

    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        self.received_request = request
        return self._plan  # type: ignore[return-value]


class UnexpectedTestPlanGenerator:
    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        raise AssertionError("Generator must not run before state validation")


def test_should_load_versioned_approved_test_context(tmp_path: Path) -> None:
    _create_test_workspace(tmp_path)

    request = load_test_generation_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert "Test Generation Prompt" in request.prompt
    assert "Export reports" in request.requirement
    assert "Use an export service" in request.design
    assert "Task T1" in request.tasks
    assert "name: reports" in request.project_metadata
    assert "Thin CLI" in request.architecture
    assert "incremental TDD" in request.conventions


def test_should_render_ordered_structured_test_plan() -> None:
    request = TestGenerationRequest(
        prompt_version="v1",
        prompt="Prompt",
        requirement="Approved requirement",
        design="Approved design",
        tasks=_task_artifact(),
        project_metadata="name: reports",
        architecture="Thin CLI",
        conventions="Incremental TDD",
    )

    rendered = render_test_plan(request, _plan())

    assert rendered.index("## Test TC1: Verify TC1") < rendered.index(
        "## Test TC2: Verify TC2"
    )
    assert "Prompt version: `v1`" in rendered
    assert "### Phase\n\nhappy_path" in rendered
    assert "### Preconditions\n\n- None identified." in rendered
    assert "### Dependencies\n\n- TC1" in rendered
    assert "### Expected outcomes" in rendered


def test_should_generate_plan_and_enter_implementation(tmp_path: Path) -> None:
    session = _create_test_workspace(tmp_path)
    generator = FakeTestPlanGenerator()

    run = run_test_generation(tmp_path, "feature-1", generator)

    assert generator.received_request is not None
    assert run.session_id == "feature-1"
    assert run.next_state == "IMPLEMENTATION"
    assert run.plan == _plan()
    assert "# Test Generation Plan" in (session / "test-plan.md").read_text(
        encoding="utf-8"
    )
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "IMPLEMENTATION"
    assert state["task_review"] == {"decision": "approved"}


@pytest.mark.parametrize(
    "state",
    [
        {
            "session_id": "feature-1",
            "state": "TASK_REVIEW",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "TEST_GENERATION",
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "TEST_GENERATION",
            "requirement_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "TEST_GENERATION",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
        },
        {
            "session_id": "another-session",
            "state": "TEST_GENERATION",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
            "task_review": {"decision": "approved"},
        },
        ["not", "an", "object"],
    ],
)
def test_should_reject_invalid_test_state_before_generator_and_mutation(
    tmp_path: Path,
    state: object,
) -> None:
    session = _create_test_workspace(tmp_path, state=state)
    original_plan = (session / "test-plan.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_test_generation(tmp_path, "feature-1", UnexpectedTestPlanGenerator())

    assert (session / "test-plan.md").read_text(encoding="utf-8") == original_plan
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize(
    "plan",
    [
        object(),
        GeneratedTestPlan("", (_case("TC1", "T1", "happy_path"),), (), ()),
        GeneratedTestPlan("Summary", (), (), ()),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "happy_path"),
                _case("TC1", "T2", "boundary", dependencies=("TC1",)),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "happy_path"),
                _case("TC2", "UNKNOWN", "boundary", dependencies=("TC1",)),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (_case("TC1", "T1", "happy_path"),),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "boundary"),
                _case("TC2", "T2", "boundary", dependencies=("TC1",)),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "happy_path"),
                _case("TC2", "T2", "regression", dependencies=("TC1",)),
                _case("TC3", "T2", "boundary", dependencies=("TC2",)),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "happy_path", dependencies=("TC2",)),
                _case("TC2", "T2", "boundary"),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                TestCasePlan(
                    test_id="TC1",
                    task_id="T1",
                    phase="happy_path",
                    title="Verify service",
                    objective="Prove behavior.",
                    test_file="tests/test_export.py",
                    test_name="test_should_export",
                    preconditions=(),
                    action="Invoke export.",
                    expected_outcomes=(),
                    dependencies=(),
                ),
                _case("TC2", "T2", "boundary", dependencies=("TC1",)),
            ),
            (),
            (),
        ),
        GeneratedTestPlan(
            "Summary",
            (
                _case("TC1", "T1", "happy_path", test_file="../secret.py"),
                _case("TC2", "T2", "boundary", dependencies=("TC1",)),
            ),
            (),
            (),
        ),
    ],
)
def test_should_reject_invalid_test_plan_before_mutation(
    tmp_path: Path,
    plan: object,
) -> None:
    session = _create_test_workspace(tmp_path)
    original_plan = (session / "test-plan.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_test_generation(
            tmp_path,
            "feature-1",
            FakeTestPlanGenerator(plan),
        )

    assert (session / "test-plan.md").read_text(encoding="utf-8") == original_plan
    assert (session / "state.json").read_text(encoding="utf-8") == original_state
