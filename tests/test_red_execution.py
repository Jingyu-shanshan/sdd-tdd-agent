import hashlib
import json
from pathlib import Path
from typing import Callable, Optional, Tuple

import pytest

from sdd_tdd_agent.red_execution import (
    MAX_EVIDENCE_STREAM_CHARACTERS,
    RedExecutionError,
    TestCommandProcessResult,
    execute_current_test_for_red,
    is_current_test_source_recorded,
    record_test_source_artifact,
)
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from sdd_tdd_agent.test_source_generation import GeneratedTestSource


TEST_CONTENT = "test('exports report', () => { expect(false).toBe(true) })\n"


def _case() -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export a report",
        "Prove export.",
        "src/export.test.ts",
        "exports report",
        (),
        "Export it.",
        ("A report is returned.",),
        (),
    )


def _workspace(root: Path, phase: str = "WRITE_TEST") -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        "test_command_timeout_seconds: 15\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": "npm@11.0.0",
                "scripts": {"test": "vitest"},
                "devDependencies": {"vitest": "4.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export\n",
        encoding="utf-8",
    )
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan("One case.", (_case(),), (), ())
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    state = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": "T1",
        "current_cycle": 1,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
        "tdd_cycle": {
            "current_test": "TC1",
            "phase": phase,
            "completed_tests": [],
        },
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    target = root / "src" / "export.test.ts"
    target.parent.mkdir()
    target.write_text(TEST_CONTENT, encoding="utf-8")
    return session


def _record(root: Path) -> None:
    record_test_source_artifact(
        root,
        "feature-1",
        GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
    )


class FixedTestRunner:
    def __init__(
        self,
        result: TestCommandProcessResult,
        during_run: Optional[Callable[[], None]] = None,
    ) -> None:
        self.result = result
        self.during_run = during_run
        self.command: Optional[Tuple[str, ...]] = None
        self.cwd: Optional[Path] = None
        self.timeout_seconds: Optional[float] = None

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        self.command = command
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        if self.during_run is not None:
            self.during_run()
        return self.result


class UnexpectedTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise AssertionError("Test runner must not be called")


class FailingTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise RedExecutionError("Test command timed out")


def test_should_record_exact_generated_test_source_digest(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    artifact = record_test_source_artifact(
        tmp_path,
        "feature-1",
        GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
    )

    expected_digest = hashlib.sha256(TEST_CONTENT.encode("utf-8")).hexdigest()
    assert artifact.test_id == "TC1"
    assert artifact.file_path == "src/export.test.ts"
    assert artifact.sha256 == expected_digest
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["test_source"] == {
        "test_id": "TC1",
        "file_path": "src/export.test.ts",
        "sha256": expected_digest,
    }


@pytest.mark.parametrize(
    "generated",
    [
        GeneratedTestSource("TC2", "src/export.test.ts", TEST_CONTENT),
        GeneratedTestSource(
            "TC1",
            "src/export.test.ts",
            "test('different', () => {})\n",
        ),
    ],
)
def test_should_reject_mismatched_generated_source_without_state_mutation(
    tmp_path: Path,
    generated: GeneratedTestSource,
) -> None:
    session = _workspace(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError):
        record_test_source_artifact(tmp_path, "feature-1", generated)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_missing_generated_source_without_state_mutation(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    (tmp_path / "src" / "export.test.ts").unlink()
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="could not be verified"):
        record_test_source_artifact(
            tmp_path,
            "feature-1",
            GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_atomic_marker_collision_without_state_mutation(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    (session / ".state.json.test-source.tmp").write_text("occupied")
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="already in progress"):
        _record(tmp_path)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_transition_to_red_for_attributable_assertion_failure(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    runner = FixedTestRunner(
        TestCommandProcessResult(1, "src/export.test.ts: exports report failed\n", "")
    )

    run = execute_current_test_for_red(tmp_path, "feature-1", runner, 15.0)

    assert runner.command is not None
    assert runner.command == (
        "npm",
        "test",
        "--",
        "--run",
        "src/export.test.ts",
        "--testNamePattern",
        r"^exports\ report$",
    )
    assert runner.cwd == tmp_path.resolve()
    assert runner.timeout_seconds == 15.0
    assert run.test_id == "TC1"
    assert run.returncode == 1
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"
    assert state["red_evidence"] == {
        "test_id": "TC1",
        "file_path": "src/export.test.ts",
        "command": list(runner.command),
        "returncode": 1,
        "stdout": "src/export.test.ts: exports report failed\n",
        "stderr": "",
    }


def test_should_accept_attributable_test_compilation_failure(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    runner = FixedTestRunner(
        TestCommandProcessResult(
            2,
            "",
            "src/export.test.ts(1,5): error TS2304: missing symbol\n",
        )
    )

    execute_current_test_for_red(tmp_path, "feature-1", runner, 8.0)

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"
    assert state["red_evidence"]["returncode"] == 2


@pytest.mark.parametrize(
    "result",
    [
        TestCommandProcessResult(0, "src/export.test.ts passed", ""),
        TestCommandProcessResult(-9, "src/export.test.ts failed", ""),
        TestCommandProcessResult(1, "", ""),
        TestCommandProcessResult(1, "another test failed", ""),
        TestCommandProcessResult(1, "No tests found: src/export.test.ts", ""),
        TestCommandProcessResult(1, "Unknown option for src/export.test.ts", ""),
    ],
)
def test_should_reject_untrustworthy_red_without_state_mutation(
    tmp_path: Path,
    result: TestCommandProcessResult,
) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            FixedTestRunner(result),
            15.0,
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_preserve_state_when_test_process_fails(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError, match="timed out"):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            FailingTestRunner(),
            15.0,
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_changed_test_before_execution(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")
    (tmp_path / "src" / "export.test.ts").write_text(
        "test('changed', () => {})\n",
        encoding="utf-8",
    )

    with pytest.raises(RedExecutionError, match="changed"):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            UnexpectedTestRunner(),
            15.0,
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_test_changed_during_execution(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    before = (session / "state.json").read_text(encoding="utf-8")

    def change_test() -> None:
        (tmp_path / "src" / "export.test.ts").write_text(
            "test('changed', () => {})\n",
            encoding="utf-8",
        )

    runner = FixedTestRunner(
        TestCommandProcessResult(1, "src/export.test.ts failed", ""),
        change_test,
    )

    with pytest.raises(RedExecutionError, match="changed"):
        execute_current_test_for_red(tmp_path, "feature-1", runner, 15.0)

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_wrong_phase_before_execution(tmp_path: Path) -> None:
    _workspace(tmp_path, phase="RED")

    with pytest.raises(ValueError, match="WRITE_TEST"):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            UnexpectedTestRunner(),
            15.0,
        )


@pytest.mark.parametrize(
    "marker",
    [
        {},
        {"test_id": "TC1", "file_path": "src/export.test.ts", "sha256": 1},
        {"test_id": "TC2", "file_path": "src/export.test.ts", "sha256": "0" * 64},
    ],
)
def test_should_reject_invalid_or_stale_source_marker_before_execution(
    tmp_path: Path,
    marker: object,
) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["test_source"] = marker
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(RedExecutionError):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            UnexpectedTestRunner(),
            15.0,
        )

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_reject_invalid_timeout_before_execution(tmp_path: Path) -> None:
    _workspace(tmp_path)
    _record(tmp_path)

    with pytest.raises(RedExecutionError, match="timeout"):
        execute_current_test_for_red(
            tmp_path,
            "feature-1",
            UnexpectedTestRunner(),
            0,
        )


def test_should_reject_unsafe_session_identifier_before_path_resolution(
    tmp_path: Path,
) -> None:
    with pytest.raises(RedExecutionError, match="identifier"):
        is_current_test_source_recorded(tmp_path, "../outside")


def test_should_translate_missing_session_state_to_safe_error(tmp_path: Path) -> None:
    with pytest.raises(RedExecutionError, match="could not be read"):
        is_current_test_source_recorded(tmp_path, "feature-1")


def test_should_sanitize_and_bound_red_evidence(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    _record(tmp_path)
    raw = (
        f"\x1b[31m{tmp_path.resolve()}/src/export.test.ts failed\x1b[0m\x00\n"
        "token=top-secret password: hidden api_key=private\n"
        "Authorization: Bearer abc.def Bearer standalone-secret\n"
        + ("x" * (MAX_EVIDENCE_STREAM_CHARACTERS + 200))
    )
    runner = FixedTestRunner(TestCommandProcessResult(1, raw, ""))

    execute_current_test_for_red(tmp_path, "feature-1", runner, 15.0)

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    output = state["red_evidence"]["stdout"]
    assert len(output) == MAX_EVIDENCE_STREAM_CHARACTERS
    assert "<PROJECT_ROOT>/src/export.test.ts failed" in output
    assert "<REDACTED>" in output
    assert "\x1b" not in output
    assert "\x00" not in output
    for secret in ("top-secret", "hidden", "private", "abc.def", "standalone"):
        assert secret not in output
