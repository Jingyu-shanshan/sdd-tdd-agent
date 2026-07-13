import json
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.task_breakdown import (
    DevelopmentTask,
    TaskBreakdown,
    TaskBreakdownRequest,
    load_task_breakdown_request,
    render_task_breakdown,
    run_task_breakdown,
)


def _task(
    task_id: str,
    title: str,
    dependencies: tuple[str, ...] = (),
) -> DevelopmentTask:
    return DevelopmentTask(
        task_id=task_id,
        title=title,
        objective=f"Implement {title.lower()}.",
        affected_areas=("sdd_tdd_agent/export.py",),
        dependencies=dependencies,
        acceptance_criteria=(f"{title} behavior is verified.",),
        test_targets=(f"test_should_{task_id.lower()}",),
    )


def _breakdown() -> TaskBreakdown:
    return TaskBreakdown(
        summary="Implement PDF export in two incremental cycles.",
        tasks=(
            _task("T1", "Export service"),
            _task("T2", "CLI integration", dependencies=("T1",)),
        ),
        global_risks=("PDF layout requirements remain unresolved.",),
        open_questions=("Which artifact is exported?",),
    )


def _create_task_workspace(
    root: Path,
    *,
    state: object = None,
    tasks: str = "# Tasks\n\nPending requirement analysis.\n",
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
    (session / "tasks.md").write_text(tasks, encoding="utf-8")
    initial_state = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "TASK_BREAKDOWN",
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


class FakeTaskGenerator:
    def __init__(self, breakdown: object = None) -> None:
        self.received_request: Optional[TaskBreakdownRequest] = None
        self._breakdown = _breakdown() if breakdown is None else breakdown

    def generate(self, request: TaskBreakdownRequest) -> TaskBreakdown:
        self.received_request = request
        return self._breakdown  # type: ignore[return-value]


class UnexpectedTaskGenerator:
    def generate(self, request: TaskBreakdownRequest) -> TaskBreakdown:
        raise AssertionError("Generator must not run before state validation")


def test_should_load_versioned_approved_task_context(tmp_path: Path) -> None:
    _create_task_workspace(tmp_path)

    request = load_task_breakdown_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert "Task Breakdown Prompt" in request.prompt
    assert "Export reports" in request.requirement
    assert "Use an export service" in request.design
    assert "name: reports" in request.project_metadata
    assert "Thin CLI" in request.architecture
    assert "incremental TDD" in request.conventions


def test_should_render_ordered_structured_tasks() -> None:
    request = TaskBreakdownRequest(
        prompt_version="v1",
        prompt="Prompt",
        requirement="Approved requirement",
        design="Approved design",
        project_metadata="name: reports",
        architecture="Thin CLI",
        conventions="Incremental TDD",
    )

    rendered = render_task_breakdown(request, _breakdown())

    assert rendered.index("## Task T1: Export service") < rendered.index(
        "## Task T2: CLI integration"
    )
    assert "Prompt version: `v1`" in rendered
    assert "### Dependencies\n\n- None identified." in rendered
    assert "### Dependencies\n\n- T1" in rendered
    assert "### Acceptance criteria" in rendered
    assert "### Test targets" in rendered


def test_should_run_injected_task_generator_and_enter_review(tmp_path: Path) -> None:
    session = _create_task_workspace(tmp_path)
    generator = FakeTaskGenerator()

    run = run_task_breakdown(tmp_path, "feature-1", generator)

    assert generator.received_request is not None
    assert run.session_id == "feature-1"
    assert run.next_state == "TASK_REVIEW"
    assert run.breakdown == _breakdown()
    assert "# Task Breakdown" in (session / "tasks.md").read_text(encoding="utf-8")
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "TASK_REVIEW"
    assert state["design_review"] == {"decision": "approved"}


@pytest.mark.parametrize(
    "state",
    [
        {
            "session_id": "feature-1",
            "state": "DESIGN_REVIEW",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "TASK_BREAKDOWN",
            "design_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "TASK_BREAKDOWN",
            "requirement_review": {"decision": "approved"},
        },
        {
            "session_id": "another-session",
            "state": "TASK_BREAKDOWN",
            "requirement_review": {"decision": "approved"},
            "design_review": {"decision": "approved"},
        },
        ["not", "an", "object"],
    ],
)
def test_should_reject_invalid_state_before_generator_and_mutation(
    tmp_path: Path,
    state: object,
) -> None:
    session = _create_task_workspace(tmp_path, state=state)
    original_tasks = (session / "tasks.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_task_breakdown(tmp_path, "feature-1", UnexpectedTaskGenerator())

    assert (session / "tasks.md").read_text(encoding="utf-8") == original_tasks
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize(
    "breakdown",
    [
        object(),
        TaskBreakdown("", (_task("T1", "Service"),), (), ()),
        TaskBreakdown("Summary", (), (), ()),
        TaskBreakdown(
            "Summary",
            (_task("T1", "Service"), _task("T1", "CLI")),
            (),
            (),
        ),
        TaskBreakdown(
            "Summary",
            (_task("T1", "Service", dependencies=("T2",)),),
            (),
            (),
        ),
        TaskBreakdown(
            "Summary",
            (
                DevelopmentTask(
                    task_id="T1",
                    title="Service",
                    objective="Implement service.",
                    affected_areas=(),
                    dependencies=(),
                    acceptance_criteria=(),
                    test_targets=("test_service",),
                ),
            ),
            (),
            (),
        ),
        TaskBreakdown(
            "Summary",
            (
                DevelopmentTask(
                    task_id="unsafe id",
                    title="Service",
                    objective="Implement service.",
                    affected_areas=(),
                    dependencies=(),
                    acceptance_criteria=("Works.",),
                    test_targets=(" ",),
                ),
            ),
            (),
            (),
        ),
    ],
)
def test_should_reject_invalid_breakdown_before_mutation(
    tmp_path: Path,
    breakdown: object,
) -> None:
    session = _create_task_workspace(tmp_path)
    original_tasks = (session / "tasks.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_task_breakdown(
            tmp_path,
            "feature-1",
            FakeTaskGenerator(breakdown),
        )

    assert (session / "tasks.md").read_text(encoding="utf-8") == original_tasks
    assert (session / "state.json").read_text(encoding="utf-8") == original_state
