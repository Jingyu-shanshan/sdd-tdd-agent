import io
import json
from pathlib import Path
from typing import Callable, Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.green_verification import (
    GreenVerificationError,
    verify_active_implementation,
)
from sdd_tdd_agent.implementation_command import continue_active_implementation
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    TestCommandProcessResult,
)
from tests.green_verification_support import create_implement_workspace


class UnexpectedModelRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError(
            "Model runner must not be called during GREEN verification"
        )


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


PASS = TestCommandProcessResult(0, "passed\n", "")
SUITE_PASS = TestCommandProcessResult(0, "all tests passed\n", "")


def test_should_run_current_test_then_full_suite_and_record_green(
    tmp_path: Path,
) -> None:
    session = create_implement_workspace(tmp_path)
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    run = continue_active_implementation(
        tmp_path,
        UnexpectedModelRunner(),
        runner,
    )

    assert run.test_id == "TC1"
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
    assert state["tdd_cycle"] == {
        "current_test": "TC1",
        "phase": "GREEN",
        "completed_tests": ["TC1"],
    }
    assert state["green_evidence"]["test_id"] == "TC1"
    assert state["green_evidence"]["current_test"]["returncode"] == 0
    assert state["green_evidence"]["full_suite"]["returncode"] == 0


def test_should_render_deterministic_green_cli_output(tmp_path: Path) -> None:
    create_implement_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["continue"],
        out=output,
        root=tmp_path,
        runner=UnexpectedModelRunner(),
        test_runner=SequenceTestRunner((PASS, SUITE_PASS)),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "GREEN confirmed: feature-1 (TC1; current test and full suite passed)\n"
    )


def test_should_return_attributable_current_failure_to_red_without_suite(
    tmp_path: Path,
) -> None:
    session = create_implement_workspace(tmp_path)
    runner = SequenceTestRunner(
        (TestCommandProcessResult(1, "src/export.test.ts failed", ""),)
    )

    with pytest.raises(GreenVerificationError, match="remains RED"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert len(runner.calls) == 1
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"
    assert state["verification_failure"] == {"stage": "current_test"}
    assert state["red_evidence"]["stdout"] == "src/export.test.ts failed"


def test_should_return_full_suite_regression_to_red(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    runner = SequenceTestRunner(
        (PASS, TestCommandProcessResult(1, "legacy behavior failed", ""))
    )

    with pytest.raises(GreenVerificationError, match="Full test suite failed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"
    assert state["verification_failure"] == {"stage": "full_suite"}
    assert state["red_evidence"]["command"] == ["npm", "test", "--", "--run"]


@pytest.mark.parametrize(
    "result",
    [
        TestCommandProcessResult(-9, "src/export.test.ts failed", ""),
        TestCommandProcessResult(1, "", ""),
        TestCommandProcessResult(1, "unrelated failure", ""),
        TestCommandProcessResult(1, "No tests found: src/export.test.ts", ""),
        TestCommandProcessResult(1, "Unknown option: src/export.test.ts", ""),
    ],
)
def test_should_preserve_implement_for_untrusted_current_failure(
    tmp_path: Path,
    result: TestCommandProcessResult,
) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            SequenceTestRunner((result,)),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "result",
    [
        TestCommandProcessResult(-9, "suite failed", ""),
        TestCommandProcessResult(1, "", ""),
        TestCommandProcessResult(1, "No tests found", ""),
        TestCommandProcessResult(1, "Unknown option", ""),
    ],
)
def test_should_preserve_implement_for_untrusted_suite_failure(
    tmp_path: Path,
    result: TestCommandProcessResult,
) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            SequenceTestRunner((PASS, result)),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_preserve_implement_when_test_process_fails(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="timed out"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            FailingTestRunner(),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_changed_production_source_before_execution(
    tmp_path: Path,
) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")
    (tmp_path / "src" / "export.ts").write_text("changed\n")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="changed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert runner.calls == []
    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_changed_test_source_before_execution(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")
    (tmp_path / "src" / "export.test.ts").write_text("changed\n")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="changed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert runner.calls == []
    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_production_source_changed_during_current_test(
    tmp_path: Path,
) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    def mutate(index: int) -> None:
        if index == 0:
            (tmp_path / "src" / "export.ts").write_text("changed\n")

    runner = SequenceTestRunner((PASS, SUITE_PASS), mutate)

    with pytest.raises(GreenVerificationError, match="changed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert len(runner.calls) == 1
    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_sanitize_and_bound_green_output(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    raw = f"\x1b[31m{tmp_path.resolve()} token=SECRET\x1b[0m\n" + ("x" * 20_000)

    continue_active_implementation(
        tmp_path,
        UnexpectedModelRunner(),
        SequenceTestRunner(
            (TestCommandProcessResult(0, raw, ""), SUITE_PASS),
        ),
    )

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    output = state["green_evidence"]["current_test"]["stdout"]
    assert len(output) == 16_000
    assert "<PROJECT_ROOT>" in output
    assert "<REDACTED>" in output
    assert "SECRET" not in output
    assert "\x1b" not in output


@pytest.mark.parametrize(
    "invalid_state",
    ["{", "[]"],
)
def test_should_reject_invalid_session_state_before_execution(
    tmp_path: Path,
    invalid_state: str,
) -> None:
    session = create_implement_workspace(tmp_path)
    (session / "state.json").write_text(invalid_state, encoding="utf-8")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="state"):
        verify_active_implementation(tmp_path, runner)

    assert runner.calls == []


@pytest.mark.parametrize(
    "artifact",
    [
        None,
        {"test_id": "TC1", "file_path": "src/export.ts", "sha256": 1},
        {"test_id": "TC1", "file_path": "../export.ts", "sha256": "0" * 64},
        {"test_id": "TC2", "file_path": "src/export.ts", "sha256": "0" * 64},
    ],
)
def test_should_reject_invalid_or_stale_production_record(
    tmp_path: Path,
    artifact: object,
) -> None:
    session = create_implement_workspace(tmp_path)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["production_source"] = artifact
    state_path.write_text(json.dumps(state), encoding="utf-8")
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="Production source record"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert runner.calls == []


def test_should_reject_missing_production_source(tmp_path: Path) -> None:
    create_implement_workspace(tmp_path)
    (tmp_path / "src" / "export.ts").unlink()
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="could not be verified"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert runner.calls == []


def test_should_reject_symlinked_production_source(tmp_path: Path) -> None:
    create_implement_workspace(tmp_path)
    source = tmp_path / "src" / "export.ts"
    replacement = tmp_path / "replacement.ts"
    replacement.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.unlink()
    source.symlink_to(replacement)
    runner = SequenceTestRunner((PASS, SUITE_PASS))

    with pytest.raises(GreenVerificationError, match="changed"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            runner,
        )

    assert runner.calls == []


def test_should_reject_state_changed_during_current_test(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    def mutate(index: int) -> None:
        if index == 0:
            state_path = session / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["concurrent"] = True
            state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(GreenVerificationError, match="concurrently"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            SequenceTestRunner((PASS, SUITE_PASS), mutate),
        )

    assert (session / "state.json").read_text(encoding="utf-8") != before


def test_should_reject_existing_atomic_state_marker(tmp_path: Path) -> None:
    session = create_implement_workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")
    marker = session / ".state.json.green-verification.tmp"
    marker.write_text("busy\n", encoding="utf-8")

    with pytest.raises(GreenVerificationError, match="already in progress"):
        continue_active_implementation(
            tmp_path,
            UnexpectedModelRunner(),
            SequenceTestRunner((PASS, SUITE_PASS)),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_missing_active_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(GreenVerificationError, match="no active Session"):
        verify_active_implementation(
            tmp_path,
            SequenceTestRunner((PASS, SUITE_PASS)),
        )
