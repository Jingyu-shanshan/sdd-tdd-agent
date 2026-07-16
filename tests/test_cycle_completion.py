import io
import json
from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.cycle_completion import (
    CycleCompletionError,
    ImplementationCompletionRun,
    complete_active_implementation,
)
from sdd_tdd_agent.implementation_command import continue_active_implementation
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.red_execution import TestCommandProcessResult
from sdd_tdd_agent.test_source_command import TestSourceCommandRun
from tests.cycle_completion_support import create_green_workspace


NEXT_TEST_CONTENT = """\
import { expect, test } from 'vitest'

test('exports empty report', () => {
  expect(true).toBe(true)
})
"""


class UnexpectedModelRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Model runner must not be called during completion")


class UnexpectedTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise AssertionError("Test runner must not be called after GREEN")


class NextTestRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls += 1
        response = {
            "test_id": "TC2",
            "file_path": "src/export.boundary.test.ts",
            "content": NEXT_TEST_CONTENT,
        }
        return ProcessResult(0, json.dumps(response), "")


def test_should_complete_exhausted_green_plan_for_review(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    before = json.loads((session / "state.json").read_text(encoding="utf-8"))

    run = continue_active_implementation(
        tmp_path,
        UnexpectedModelRunner(),
        UnexpectedTestRunner(),
    )

    assert isinstance(run, ImplementationCompletionRun)
    assert run.session_id == "feature-1"
    assert run.completed_tests == ("TC1",)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "REVIEW"
    assert state["current_task"] is None
    assert state["tdd_cycle"] == before["tdd_cycle"]
    assert state["green_evidence"] == before["green_evidence"]
    assert state["test_source"] == before["test_source"]
    assert state["production_source"] == before["production_source"]


def test_should_render_deterministic_review_ready_output(tmp_path: Path) -> None:
    create_green_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["continue"],
        out=output,
        root=tmp_path,
        runner=UnexpectedModelRunner(),
        test_runner=UnexpectedTestRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Implementation ready for review: feature-1 (1 tests GREEN)\n"
    )


def test_should_start_only_next_test_and_clear_prior_cycle_evidence(
    tmp_path: Path,
) -> None:
    session = create_green_workspace(tmp_path, include_next=True)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["verification_failure"] = {"stage": "old"}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    model_runner = NextTestRunner()

    run = continue_active_implementation(
        tmp_path,
        model_runner,
        UnexpectedTestRunner(),
    )

    assert isinstance(run, TestSourceCommandRun)
    assert run.test_id == "TC2"
    assert model_runner.calls == 1
    updated = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated["tdd_cycle"] == {
        "current_test": "TC2",
        "phase": "WRITE_TEST",
        "completed_tests": ["TC1"],
    }
    assert updated["test_source"]["test_id"] == "TC2"
    for stale in (
        "red_evidence",
        "production_source",
        "green_evidence",
        "verification_failure",
    ):
        assert stale not in updated


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("missing", None),
        ("test_id", "TC2"),
        ("current_returncode", 1),
        ("suite_command", []),
        ("suite_stdout", "token=SECRET"),
        ("suite_stderr", 1),
        ("suite_stderr", "\ud800"),
        ("current_result", None),
        ("extra", True),
    ],
)
def test_should_reject_invalid_green_evidence_without_mutation(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    session = create_green_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    evidence = state["green_evidence"]
    if field == "missing":
        state.pop("green_evidence")
    elif field == "test_id":
        evidence["test_id"] = value
    elif field == "current_returncode":
        evidence["current_test"]["returncode"] = value
    elif field == "suite_command":
        evidence["full_suite"]["command"] = value
    elif field == "suite_stdout":
        evidence["full_suite"]["stdout"] = value
    elif field == "suite_stderr":
        evidence["full_suite"]["stderr"] = value
    elif field == "current_result":
        evidence["current_test"] = value
    else:
        evidence["unexpected"] = value
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(CycleCompletionError, match="GREEN evidence"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            UnexpectedTestRunner(),
        )

    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("changed_file", ["src/export.ts", "src/export.test.ts"])
def test_should_reject_changed_final_source_without_mutation(
    tmp_path: Path,
    changed_file: str,
) -> None:
    session = create_green_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    (tmp_path / changed_file).write_text("changed\n", encoding="utf-8")

    with pytest.raises(CycleCompletionError, match="changed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            UnexpectedTestRunner(),
        )

    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_atomic_completion_collision(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    (session / ".state.json.cycle-completion.tmp").write_text(
        "busy\n",
        encoding="utf-8",
    )

    with pytest.raises(CycleCompletionError, match="already in progress"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            UnexpectedTestRunner(),
        )

    assert state_path.read_text(encoding="utf-8") == before


def test_should_translate_unwritable_completion_state(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    session.chmod(0o555)

    try:
        with pytest.raises(CycleCompletionError, match="could not be updated"):
            complete_active_implementation(tmp_path)
    finally:
        session.chmod(0o755)

    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_direct_completion_with_remaining_test(tmp_path: Path) -> None:
    session = create_green_workspace(tmp_path, include_next=True)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(CycleCompletionError, match="remain"):
        complete_active_implementation(tmp_path)

    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(CycleCompletionError, match="no active Session"):
        complete_active_implementation(tmp_path)


def test_should_translate_unreadable_project_status(tmp_path: Path) -> None:
    with pytest.raises(CycleCompletionError, match="status could not be read"):
        complete_active_implementation(tmp_path)
