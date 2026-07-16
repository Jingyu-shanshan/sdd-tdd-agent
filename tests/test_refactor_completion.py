import io
import json
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.cycle_completion import canonical_json_sha256
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    TestCommandProcessResult,
)
from sdd_tdd_agent.refactor_completion import (
    RefactorVerificationError,
    complete_active_refactor,
)
from tests.refactor_completion_support import create_refactor_workspace


PASS = TestCommandProcessResult(0, "passed\n", "")
SUITE_PASS = TestCommandProcessResult(0, "all tests passed\n", "")


def _write_rehashed_state(state_path: Path, state: dict[str, Any]) -> None:
    completion = state["implementation_completion"]
    completion["green_evidence_sha256"] = canonical_json_sha256(state["green_evidence"])
    state["implementation_review"]["completion_sha256"] = canonical_json_sha256(
        completion
    )
    state_path.write_text(json.dumps(state), encoding="utf-8")


class SequenceTestRunner:
    def __init__(
        self,
        results: Tuple[TestCommandProcessResult, ...],
        after_call: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.results = results
        self.after_call = after_call
        self.calls: list[tuple[Tuple[str, ...], Path, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        index = len(self.calls)
        self.calls.append((command, cwd, timeout_seconds))
        if self.after_call is not None:
            self.after_call(index)
        return self.results[index]


class FailingTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise RedExecutionError("Test command timed out")


def test_should_verify_refactor_and_enter_done(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    run = complete_active_refactor(tmp_path, runner)

    assert run.session_id == "feature-1"
    assert run.completed_test_count == 1
    assert [call[0] for call in runner.calls] == [
        (
            "npm",
            "test",
            "--",
            "--run",
            "src/export.test.ts",
            "--testNamePattern",
            r"^exports\ report$",
        ),
        ("npm", "test", "--", "--run"),
    ]
    assert [call[2] for call in runner.calls] == [15.0, 60.0]
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DONE"
    assert state["refactor"] == {
        "mode": "no_source_change",
        "decision": "verified",
    }
    assert state["final_verification"]["current_test"]["returncode"] == 0
    assert state["final_verification"]["full_suite"]["returncode"] == 0


def test_should_render_deterministic_refactor_cli_output(tmp_path: Path) -> None:
    create_refactor_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["refactor"],
        out=output,
        root=tmp_path,
        test_runner=SequenceTestRunner((PASS, SUITE_PASS)),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Refactor verification complete: feature-1 (1 tests; DONE)\n"
    )


def test_should_preserve_refactor_when_current_test_fails(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    runner = SequenceTestRunner((TestCommandProcessResult(1, "failed", ""),))

    with pytest.raises(RefactorVerificationError, match="Current test failed"):
        complete_active_refactor(tmp_path, runner)

    assert len(runner.calls) == 1
    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "result",
    [
        TestCommandProcessResult(1, "regression", ""),
        TestCommandProcessResult(-9, "terminated", ""),
    ],
)
def test_should_preserve_refactor_when_full_suite_fails(
    tmp_path: Path,
    result: TestCommandProcessResult,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="Full test suite failed"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, result)),
        )

    assert state_path.read_text(encoding="utf-8") == before


def test_should_preserve_refactor_when_runner_fails(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="timed out"):
        complete_active_refactor(tmp_path, FailingTestRunner())

    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "changed_file",
    ["src/export.ts", "src/export.test.ts", ".agent/sessions/feature-1/review.md"],
)
def test_should_reject_changed_final_artifact_before_execution(
    tmp_path: Path,
    changed_file: str,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    (tmp_path / changed_file).write_text("changed\n", encoding="utf-8")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(RefactorVerificationError, match="changed|stale"):
        complete_active_refactor(tmp_path, runner)

    assert runner.calls == []
    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_tampered_recorded_command_before_execution(
    tmp_path: Path,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["green_evidence"]["current_test"]["command"] = ["sh", "-c", "test"]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(RefactorVerificationError, match="completion|command"):
        complete_active_refactor(tmp_path, runner)

    assert runner.calls == []


@pytest.mark.parametrize("raw_state", ["{", "[]"])
def test_should_reject_invalid_session_state(
    tmp_path: Path,
    raw_state: str,
) -> None:
    session = create_refactor_workspace(tmp_path)
    (session / "state.json").write_text(raw_state, encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="Project status"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


@pytest.mark.parametrize(
    ("record", "message"),
    [
        ("implementation_completion", "completion"),
        ("implementation_review", "review"),
        ("green_evidence", "GREEN evidence"),
    ],
)
def test_should_reject_missing_audit_record(
    tmp_path: Path,
    record: str,
    message: str,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    del state[record]
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match=message):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_invalid_green_digest(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["implementation_completion"]["green_evidence_sha256"] = "invalid"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="digest is invalid"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_stale_review_decision(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["implementation_review"]["decision"] = "unverified"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="review is stale"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_symlinked_review_report(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    report = session / "review.md"
    replacement = tmp_path / "review.md"
    replacement.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
    report.unlink()
    report.symlink_to(replacement)

    with pytest.raises(RefactorVerificationError, match="Review report changed"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_unsafe_final_test_path(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["test_source"]["file_path"] = "../outside.test.ts"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="path is unsafe"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


@pytest.mark.parametrize("artifact", ["test_source", "production_source"])
def test_should_reject_invalid_final_artifact_record(
    tmp_path: Path,
    artifact: str,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state[artifact] = {"unexpected": True}
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="artifact is invalid"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


@pytest.mark.parametrize("relative_path", ["src/export.ts", "src/export.test.ts"])
def test_should_reject_missing_final_source(
    tmp_path: Path,
    relative_path: str,
) -> None:
    create_refactor_workspace(tmp_path)
    (tmp_path / relative_path).unlink()

    with pytest.raises(RefactorVerificationError, match="could not be read"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_symlinked_final_source(tmp_path: Path) -> None:
    create_refactor_workspace(tmp_path)
    source = tmp_path / "src" / "export.ts"
    replacement = tmp_path / "replacement.ts"
    replacement.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.unlink()
    source.symlink_to(replacement)

    with pytest.raises(RefactorVerificationError, match="artifact changed"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_unsanitized_green_evidence(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["green_evidence"]["current_test"]["stdout"] = str(tmp_path.resolve())
    _write_rehashed_state(state_path, state)

    with pytest.raises(RefactorVerificationError, match="GREEN evidence"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_boolean_green_returncode(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["green_evidence"]["current_test"]["returncode"] = False
    _write_rehashed_state(state_path, state)

    with pytest.raises(RefactorVerificationError, match="recorded command"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )


def test_should_reject_source_changed_during_current_test(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    def mutate(index: int) -> None:
        if index == 0:
            (tmp_path / "src" / "export.ts").write_text("changed\n")

    runner = SequenceTestRunner((PASS, SUITE_PASS), mutate)

    with pytest.raises(RefactorVerificationError, match="changed"):
        complete_active_refactor(tmp_path, runner)

    assert len(runner.calls) == 1
    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_source_changed_during_full_suite(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    def mutate(index: int) -> None:
        if index == 1:
            (tmp_path / "src" / "export.ts").write_text(
                "changed\n",
                encoding="utf-8",
            )

    runner = SequenceTestRunner((PASS, SUITE_PASS), mutate)

    with pytest.raises(RefactorVerificationError, match="changed"):
        complete_active_refactor(tmp_path, runner)

    assert len(runner.calls) == 2
    assert state_path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("changed_call", [0, 1])
def test_should_reject_state_changed_during_verification(
    tmp_path: Path,
    changed_call: int,
) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"

    def mutate(index: int) -> None:
        if index == changed_call:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["concurrent_change"] = True
            state_path.write_text(json.dumps(state), encoding="utf-8")

    runner = SequenceTestRunner((PASS, SUITE_PASS), mutate)

    with pytest.raises(RefactorVerificationError, match="changed concurrently"):
        complete_active_refactor(tmp_path, runner)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["state"] == "REFACTOR"
    assert "final_verification" not in state
    assert len(runner.calls) == changed_call + 1


def test_should_sanitize_and_bound_final_output(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    raw = f"\x1b[31m{tmp_path.resolve()} token=SECRET\x1b[0m\n" + ("x" * 20_000)

    complete_active_refactor(
        tmp_path,
        SequenceTestRunner((TestCommandProcessResult(0, raw, ""), SUITE_PASS)),
    )

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    output = state["final_verification"]["current_test"]["stdout"]
    assert len(output) == 16_000
    assert "<PROJECT_ROOT>" in output
    assert "<REDACTED>" in output
    assert "SECRET" not in output
    assert "\x1b" not in output


def test_should_preserve_atomic_collision_marker(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")
    marker = session / ".state.json.refactor.tmp"
    marker.write_text("busy\n", encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="already in progress"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )

    assert state_path.read_text(encoding="utf-8") == before
    assert marker.read_text(encoding="utf-8") == "busy\n"


def test_should_reject_non_refactor_state_without_mutation(tmp_path: Path) -> None:
    session = create_refactor_workspace(tmp_path)
    complete_active_refactor(
        tmp_path,
        SequenceTestRunner((PASS, SUITE_PASS)),
    )
    state_path = session / "state.json"
    before = state_path.read_text(encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="REFACTOR"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )

    assert state_path.read_text(encoding="utf-8") == before


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(RefactorVerificationError, match="no active Session"):
        complete_active_refactor(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )
