import hashlib
import io
import json
from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    TestCommandProcessResult,
)
from sdd_tdd_agent.telemetry import (
    ObservedProcessRunner,
    ObservedTestCommandRunner,
    TelemetryError,
    TelemetryEvent,
    TelemetryRecorder,
    load_session_metrics,
    observe_process_runner,
    observe_test_runner,
    render_session_metrics,
)


class Clock:
    def __init__(self, values: Tuple[float, ...]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> float:
        value = self.values[self.index]
        self.index += 1
        return value


class ProcessRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[Tuple[str, ...], str, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, stdin, timeout_seconds))
        return self.result


class FailingProcessRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise RuntimeError("provider payload SECRET")


class FakeTestRunner:
    def __init__(self, result: TestCommandProcessResult) -> None:
        self.result = result

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        return self.result


class FailingTestRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        raise RedExecutionError("test output SECRET")


def _recorder(root: Path) -> TelemetryRecorder:
    return TelemetryRecorder(root, "feature-1")


def _events(root: Path) -> list[dict[str, object]]:
    path = root / ".agent" / "metrics" / "feature-1.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_should_record_model_metadata_without_payload(tmp_path: Path) -> None:
    delegate = ProcessRunner(ProcessResult(0, "SOURCE OUTPUT", "SECRET"))
    runner = ObservedProcessRunner(
        delegate,
        _recorder(tmp_path),
        "requirement_analysis",
        clock=Clock((10.0, 10.25)),
    )
    stdin = json.dumps(
        {
            "prompt_version": "v1",
            "prompt": "PRIVATE PROMPT",
            "source": "PRIVATE SOURCE",
        }
    )

    result = runner.run(("/private/bin/provider", "--secret"), stdin, 30.0)

    assert result.stdout == "SOURCE OUTPUT"
    event = _events(tmp_path)[0]
    assert event == {
        "schema_version": 1,
        "session_id": "feature-1",
        "operation": "requirement_analysis",
        "kind": "model",
        "tool": "provider",
        "success": True,
        "returncode": 0,
        "duration_seconds": 0.25,
        "prompt_version": "v1",
        "prompt_sha256": (hashlib.sha256(b"PRIVATE PROMPT").hexdigest()),
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "usage_status": "unavailable",
    }
    serialized = json.dumps(event)
    for secret in ("PRIVATE PROMPT", "PRIVATE SOURCE", "--secret", "SOURCE OUTPUT"):
        assert secret not in serialized


def test_should_record_and_reraise_model_failure(tmp_path: Path) -> None:
    runner = ObservedProcessRunner(
        FailingProcessRunner(),
        _recorder(tmp_path),
        "design_generation",
        clock=Clock((1.0, 1.5)),
    )

    with pytest.raises(RuntimeError, match="provider payload"):
        runner.run(("provider",), "PRIVATE", 30.0)

    event = _events(tmp_path)[0]
    assert event["success"] is False
    assert event["returncode"] is None
    assert "SECRET" not in json.dumps(event)


@pytest.mark.parametrize(
    ("delegate", "returncode", "raises"),
    [
        (FakeTestRunner(TestCommandProcessResult(0, "passed", "")), 0, False),
        (FailingTestRunner(), None, True),
    ],
)
def test_should_record_test_result_without_command_or_output(
    tmp_path: Path,
    delegate: object,
    returncode: object,
    raises: bool,
) -> None:
    runner = ObservedTestCommandRunner(
        delegate,  # type: ignore[arg-type]
        _recorder(tmp_path),
        "green_verification",
        clock=Clock((2.0, 3.0)),
    )

    if raises:
        with pytest.raises(RedExecutionError):
            runner.run(("npm", "test", "SECRET"), tmp_path, 10.0)
    else:
        runner.run(("npm", "test", "SECRET"), tmp_path, 10.0)

    event = _events(tmp_path)[0]
    assert event["kind"] == "test"
    assert event["returncode"] == returncode
    assert "SECRET" not in json.dumps(event)


def test_should_aggregate_and_render_metrics(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    ObservedProcessRunner(
        ProcessRunner(ProcessResult(0, "", "")),
        recorder,
        "design_generation",
        clock=Clock((0.0, 0.5)),
    ).run(("codex",), "{}", 10.0)
    ObservedTestCommandRunner(
        FakeTestRunner(TestCommandProcessResult(1, "", "")),
        recorder,
        "red_execution",
        clock=Clock((1.0, 2.5)),
    ).run(("pytest",), tmp_path, 10.0)

    metrics = load_session_metrics(tmp_path, "feature-1")

    assert metrics.event_count == 2
    assert metrics.model_calls == 1
    assert metrics.test_calls == 1
    assert metrics.successful_calls == 1
    assert metrics.duration_seconds == 2.0
    assert metrics.input_tokens is None
    assert metrics.cost_usd is None
    assert render_session_metrics(metrics) == (
        "Session metrics: feature-1\n"
        "Calls: 2 (1 successful, 50.00%)\n"
        "Model calls: 1\n"
        "Test calls: 1\n"
        "Duration: 2.000000s\n"
        "Tokens: unavailable\n"
        "Cost USD: unavailable\n"
    )


def test_should_reject_malformed_metrics(tmp_path: Path) -> None:
    path = tmp_path / ".agent" / "metrics" / "feature-1.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{\n", encoding="utf-8")

    with pytest.raises(TelemetryError, match="invalid"):
        load_session_metrics(tmp_path, "feature-1")


def test_should_render_active_metrics_cli(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        '{"session_id":"feature-1","state":"ANALYSIS"}',
        encoding="utf-8",
    )
    recorder = _recorder(tmp_path)
    ObservedProcessRunner(
        ProcessRunner(ProcessResult(0, "", "")),
        recorder,
        "requirement_analysis",
        clock=Clock((0.0, 0.25)),
    ).run(("codex",), "{}", 10.0)
    output = io.StringIO()

    exit_code = main(["metrics"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Session metrics: feature-1\nCalls: 1")


def test_should_aggregate_verified_reported_usage(tmp_path: Path) -> None:
    _recorder(tmp_path).record(
        TelemetryEvent(
            1,
            "feature-1",
            "provider_call",
            "model",
            "codex",
            True,
            0,
            0.5,
            "v1",
            hashlib.sha256(b"prompt").hexdigest(),
            10,
            4,
            0.25,
            "reported",
        )
    )

    metrics = load_session_metrics(tmp_path, "feature-1")

    assert metrics.input_tokens == 10
    assert metrics.output_tokens == 4
    assert metrics.cost_usd == 0.25
    assert "Tokens: 14\nCost USD: 0.250000\n" in render_session_metrics(metrics)


def test_should_return_empty_metrics_when_no_events_exist(tmp_path: Path) -> None:
    metrics = load_session_metrics(tmp_path, "feature-1")

    assert metrics.event_count == 0
    assert "0 successful, n/a" in render_session_metrics(metrics)


@pytest.mark.parametrize(
    ("session_id", "operation"),
    [("../unsafe", "valid"), ("feature-1", "INVALID OPERATION")],
)
def test_should_reject_unsafe_telemetry_identity(
    tmp_path: Path,
    session_id: str,
    operation: str,
) -> None:
    if session_id != "feature-1":
        with pytest.raises(TelemetryError, match="Session"):
            TelemetryRecorder(tmp_path, session_id)
        return
    with pytest.raises(TelemetryError, match="operation"):
        ObservedProcessRunner(
            ProcessRunner(ProcessResult(0, "", "")),
            _recorder(tmp_path),
            operation,
        )


def test_should_reject_unsafe_metrics_path(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "metrics").symlink_to(outside, target_is_directory=True)

    with pytest.raises(TelemetryError, match="unsafe"):
        _recorder(tmp_path).record(
            TelemetryEvent(
                1,
                "feature-1",
                "provider_call",
                "model",
                "codex",
                True,
                0,
                0.1,
                None,
                None,
                None,
                None,
                None,
                "unavailable",
            )
        )


def test_should_wrap_only_when_a_session_is_active(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    project = workspace / "project.yml"
    project.write_text("name: reports\n", encoding="utf-8")
    process = ProcessRunner(ProcessResult(0, "", ""))
    tests = FakeTestRunner(TestCommandProcessResult(0, "", ""))

    assert observe_process_runner(tmp_path, "provider_call", process) is process
    assert observe_test_runner(tmp_path, "test_call", tests) is tests

    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (session / "state.json").write_text(
        '{"session_id":"feature-1","state":"ANALYSIS"}',
        encoding="utf-8",
    )
    project.write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )

    assert isinstance(
        observe_process_runner(tmp_path, "provider_call", process),
        ObservedProcessRunner,
    )
    assert isinstance(
        observe_test_runner(tmp_path, "test_call", tests),
        ObservedTestCommandRunner,
    )


def test_should_observe_public_workflow_model_call(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        "requirement_analyzer_command:\n"
        '  - "bridge"\n'
        "requirement_analyzer_timeout_seconds: 30\n",
        encoding="utf-8",
    )
    (workspace / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (workspace / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    (session / "requirement.md").write_text(
        "# Requirement\n\n## User request\n\nExport reports\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "ANALYSIS",
                "current_task": None,
                "current_cycle": 0,
            }
        ),
        encoding="utf-8",
    )
    response = {
        "summary": "Export reports.",
        "user_stories": ["A user exports a report."],
        "functional_requirements": ["Provide export."],
        "non_functional_requirements": [],
        "impact_analysis": [],
        "open_questions": [],
    }

    exit_code = main(
        ["analyze"],
        root=tmp_path,
        out=io.StringIO(),
        runner=ProcessRunner(ProcessResult(0, json.dumps(response), "")),
    )

    assert exit_code == 0
    assert _events(tmp_path)[0]["operation"] == "requirement_analysis"
