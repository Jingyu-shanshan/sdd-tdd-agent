import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.failure_memory import (
    FailureMemoryError,
    load_failure_memories,
    record_failure,
    render_failure_memories,
)
from sdd_tdd_agent.quality_metrics import (
    QualityMetricsError,
    load_session_quality_metrics,
)
from sdd_tdd_agent.red_execution import TestCommandProcessResult
from sdd_tdd_agent.telemetry import (
    ObservedTestCommandRunner,
    TelemetryEvent,
    TelemetryRecorder,
)
from sdd_tdd_agent.tdd_cycle import load_planned_test_cases
from tests.cycle_completion_support import create_green_workspace


class Clock:
    def __init__(self, values: Tuple[float, ...]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> float:
        value = self.values[self.index]
        self.index += 1
        return value


class ResultRunner:
    def __init__(self, result: TestCommandProcessResult) -> None:
        self.result = result

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        return self.result


def _event(
    session_id: str,
    operation: str,
    success: bool,
    returncode: int,
    duration: float,
) -> TelemetryEvent:
    return TelemetryEvent(
        1,
        session_id,
        operation,
        "test",
        "npm",
        success,
        returncode,
        duration,
        None,
        None,
        None,
        None,
        None,
        "unavailable",
    )


def test_should_merge_content_free_failure_memory_across_sessions(
    tmp_path: Path,
) -> None:
    for session_id in ("feature-1", "feature-2", "feature-1"):
        ObservedTestCommandRunner(
            ResultRunner(TestCommandProcessResult(1, "PRIVATE SOURCE", "SECRET")),
            TelemetryRecorder(tmp_path, session_id),
            "tdd_test_execution",
            clock=Clock((0.0, 0.5)),
        ).run(("npm", "test", "--token=SECRET"), tmp_path, 10.0)

    memories = load_failure_memories(tmp_path)

    assert len(memories) == 1
    memory = memories[0]
    assert memory.occurrences == 3
    assert memory.session_ids == ("feature-1", "feature-2")
    assert memory.failure_mode == "nonzero_exit"
    assert memory.returncode == 1
    serialized = (tmp_path / ".agent" / "memories" / "failures.json").read_text()
    for private in ("PRIVATE SOURCE", "SECRET", "--token"):
        assert private not in serialized


def test_should_merge_exception_failure_without_error_text(tmp_path: Path) -> None:
    record_failure(
        tmp_path,
        "feature-1",
        "design_generation",
        "model",
        "codex",
        "exception",
        None,
    )

    memory = load_failure_memories(tmp_path)[0]

    assert memory.failure_mode == "exception"
    assert memory.returncode is None


def test_should_render_failures_deterministically(tmp_path: Path) -> None:
    record_failure(
        tmp_path,
        "feature-1",
        "red_execution",
        "test",
        "pytest",
        "nonzero_exit",
        1,
    )

    rendered = render_failure_memories(load_failure_memories(tmp_path))

    assert rendered.startswith("Failure memory: 1 signatures\n")
    assert (
        "red_execution | test | pytest | nonzero_exit (exit 1) | 1 occurrences"
        in rendered
    )


def test_should_preserve_preexisting_failure_update_collision(tmp_path: Path) -> None:
    directory = tmp_path / ".agent" / "memories"
    directory.mkdir(parents=True)
    collision = directory / ".failures.json.tmp"
    collision.write_text("owned", encoding="utf-8")

    with pytest.raises(FailureMemoryError, match="already in progress"):
        record_failure(
            tmp_path,
            "feature-1",
            "red_execution",
            "test",
            "pytest",
            "nonzero_exit",
            1,
        )

    assert collision.read_text() == "owned"


def test_should_reject_tampered_failure_memory(tmp_path: Path) -> None:
    path = tmp_path / ".agent" / "memories" / "failures.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":1,"failures":[{"secret":"value"}]}')

    with pytest.raises(FailureMemoryError, match="invalid"):
        load_failure_memories(tmp_path)


def test_should_project_exact_task_and_test_completion(tmp_path: Path) -> None:
    create_green_workspace(tmp_path, include_next=True)
    recorder = TelemetryRecorder(tmp_path, "feature-1")
    recorder.record(_event("feature-1", "tdd_test_execution", True, 0, 1.0))
    recorder.record(_event("feature-1", "tdd_test_execution", False, 1, 3.0))
    recorder.record(_event("feature-1", "refactor_verification", True, 0, 2.0))

    cases = load_planned_test_cases(tmp_path, "feature-1")
    metrics = load_session_quality_metrics(tmp_path, "feature-1")

    assert len(cases) == 2
    assert metrics.planned_tasks == 2
    assert metrics.completed_tasks == 1
    assert metrics.task_completion_rate == 0.5
    assert metrics.planned_tests == 2
    assert metrics.completed_tests == 1
    assert metrics.test_completion_rate == 0.5
    assert metrics.build_test_success_rate == 2 / 3
    assert metrics.refactor_success_rate == 1.0
    assert metrics.mean_call_duration_seconds == 2.0
    assert metrics.cost_per_feature_usd is None


def test_should_render_quality_metrics_cli(tmp_path: Path) -> None:
    create_green_workspace(tmp_path, include_next=True)
    output = io.StringIO()

    exit_code = main(["metrics", "quality"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (
        "Session quality: feature-1\n"
        "Tasks: 1/2 (50.00%)\n"
        "Tests: 1/2 (50.00%)\n"
        "Build/test success: unavailable\n"
        "Refactor success: unavailable\n"
        "Mean call duration: unavailable\n"
        "Cost per feature USD: unavailable\n"
    )


def test_should_render_failure_memory_cli(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    record_failure(
        tmp_path,
        "feature-1",
        "red_execution",
        "test",
        "pytest",
        "nonzero_exit",
        1,
    )
    output = io.StringIO()

    exit_code = main(["failures"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Failure memory: 1 signatures\n")


@pytest.mark.parametrize(
    ("session_id", "operation", "kind", "tool", "mode", "returncode"),
    [
        ("../unsafe", "red_execution", "test", "pytest", "nonzero_exit", 1),
        ("feature-1", "red_execution", "other", "pytest", "nonzero_exit", 1),
        ("feature-1", "red_execution", "test", "pytest", "other", 1),
        ("feature-1", "red_execution", "test", "pytest", "exception", 1),
    ],
)
def test_should_reject_invalid_failure_signature(
    tmp_path: Path,
    session_id: str,
    operation: str,
    kind: str,
    tool: str,
    mode: str,
    returncode: Optional[int],
) -> None:
    with pytest.raises(FailureMemoryError):
        record_failure(
            tmp_path,
            session_id,
            operation,
            kind,
            tool,
            mode,
            returncode,
        )


def test_should_reject_symlinked_failure_memory_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "memories").symlink_to(outside, target_is_directory=True)

    with pytest.raises(FailureMemoryError, match="unsafe"):
        load_failure_memories(tmp_path)


def test_should_reject_invalid_fingerprint_and_order(tmp_path: Path) -> None:
    first = record_failure(
        tmp_path,
        "feature-1",
        "red_execution",
        "test",
        "pytest",
        "nonzero_exit",
        1,
    )
    record_failure(
        tmp_path,
        "feature-1",
        "design_generation",
        "model",
        "codex",
        "exception",
        None,
    )
    path = tmp_path / ".agent" / "memories" / "failures.json"
    value = json.loads(path.read_text())
    value["failures"].reverse()
    path.write_text(json.dumps(value))
    with pytest.raises(FailureMemoryError, match="invalid"):
        load_failure_memories(tmp_path)

    value["failures"].sort(key=lambda item: item["fingerprint"])
    for item in value["failures"]:
        if item["fingerprint"] == first.fingerprint:
            item["fingerprint"] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(FailureMemoryError, match="fingerprint"):
        load_failure_memories(tmp_path)


def test_should_reject_stale_quality_prefix_and_allow_no_progress(
    tmp_path: Path,
) -> None:
    session = create_green_workspace(tmp_path, include_next=True)
    state_path = session / "state.json"
    state = json.loads(state_path.read_text())
    state.pop("tdd_cycle")
    state_path.write_text(json.dumps(state))

    assert load_session_quality_metrics(tmp_path, "feature-1").completed_tests == 0

    state["tdd_cycle"] = {
        "current_test": "TC2",
        "phase": "GREEN",
        "completed_tests": ["TC2"],
    }
    state_path.write_text(json.dumps(state))
    with pytest.raises(QualityMetricsError, match="stale"):
        load_session_quality_metrics(tmp_path, "feature-1")
