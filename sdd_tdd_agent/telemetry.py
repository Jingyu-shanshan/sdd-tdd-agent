import hashlib
import json
import math
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, ClassVar, Dict, Optional, Tuple, cast

from sdd_tdd_agent.model_adapter import (
    ProcessResult,
    ProcessRunner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    TestCommandProcessResult,
    TestCommandRunner,
)


SCHEMA_VERSION = 1
MAX_METRICS_BYTES = 10_000_000
MAX_EVENT_BYTES = 4_096
SESSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
OPERATION_PATTERN = re.compile(r"[a-z][a-z0-9_.:-]*")
TOOL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
EVENT_FIELDS = {
    "schema_version",
    "session_id",
    "operation",
    "kind",
    "tool",
    "success",
    "returncode",
    "duration_seconds",
    "prompt_version",
    "prompt_sha256",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "usage_status",
}


class TelemetryError(RuntimeError):
    """Safe public error for telemetry recording and aggregation."""


@dataclass(frozen=True)
class TelemetryEvent:
    """One privacy-safe model or test execution event."""

    schema_version: int
    session_id: str
    operation: str
    kind: str
    tool: str
    success: bool
    returncode: Optional[int]
    duration_seconds: float
    prompt_version: Optional[str]
    prompt_sha256: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[float]
    usage_status: str


@dataclass(frozen=True)
class SessionMetrics:
    """Validated aggregate metrics for one Session."""

    session_id: str
    event_count: int
    model_calls: int
    test_calls: int
    successful_calls: int
    duration_seconds: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[float]


def _session_id(value: str) -> str:
    if SESSION_PATTERN.fullmatch(value) is None:
        raise TelemetryError("Telemetry Session identifier is invalid")
    return value


def _operation(value: str) -> str:
    if OPERATION_PATTERN.fullmatch(value) is None or len(value) > 80:
        raise TelemetryError("Telemetry operation is invalid")
    return value


def _tool(command: Tuple[str, ...]) -> str:
    if not command or not isinstance(command[0], str):
        raise TelemetryError("Telemetry command is invalid")
    name = PurePosixPath(command[0].replace("\\", "/")).name
    return name if TOOL_PATTERN.fullmatch(name) is not None else "custom"


def _duration(start: float, end: float) -> float:
    value = end - start
    if not math.isfinite(value) or value < 0:
        raise TelemetryError("Telemetry duration is invalid")
    return round(value, 6)


def _prompt_identity(stdin: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        value = json.loads(stdin)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(value, dict):
        return None, None
    version = value.get("prompt_version")
    prompt = value.get("prompt")
    if not isinstance(version, str) or not version or not isinstance(prompt, str):
        return None, None
    return version[:80], hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _event(
    session_id: str,
    operation: str,
    kind: str,
    command: Tuple[str, ...],
    success: bool,
    returncode: Optional[int],
    duration_seconds: float,
    prompt: Tuple[Optional[str], Optional[str]] = (None, None),
) -> TelemetryEvent:
    return TelemetryEvent(
        SCHEMA_VERSION,
        session_id,
        _operation(operation),
        kind,
        _tool(command),
        success,
        returncode,
        duration_seconds,
        prompt[0],
        prompt[1],
        None,
        None,
        None,
        "unavailable",
    )


class TelemetryRecorder:
    """Append bounded privacy-safe events below one project workspace."""

    def __init__(self, root: Path, session_id: str) -> None:
        self._root = root.resolve()
        self.session_id = _session_id(session_id)

    def record(self, event: TelemetryEvent) -> None:
        """Validate and append one canonical JSON event with no output payload."""
        _validate_event(asdict(event), self.session_id)
        path = _metrics_path(self._root, self.session_id, create=True)
        serialized = (
            json.dumps(asdict(event), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        if len(serialized) > MAX_EVENT_BYTES:
            raise TelemetryError("Telemetry event is too large")
        try:
            if (
                path.exists()
                and path.stat().st_size + len(serialized) > MAX_METRICS_BYTES
            ):
                raise TelemetryError("Telemetry file is too large")
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            try:
                if os.write(descriptor, serialized) != len(serialized):
                    raise TelemetryError("Telemetry event could not be written")
            finally:
                os.close(descriptor)
        except OSError as error:
            raise TelemetryError("Telemetry event could not be recorded") from error


class ObservedProcessRunner:
    """Record one event around an existing model-process runner."""

    def __init__(
        self,
        delegate: ProcessRunner,
        recorder: TelemetryRecorder,
        operation: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._operation = _operation(operation)
        self._clock = clock

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        """Delegate unchanged while recording only allowlisted metadata."""
        start = self._clock()
        prompt = _prompt_identity(stdin)
        try:
            result = self._delegate.run(command, stdin, timeout_seconds)
        except Exception:
            self._recorder.record(
                _event(
                    self._recorder.session_id,
                    self._operation,
                    "model",
                    command,
                    False,
                    None,
                    _duration(start, self._clock()),
                    prompt,
                )
            )
            raise
        self._recorder.record(
            _event(
                self._recorder.session_id,
                self._operation,
                "model",
                command,
                result.returncode == 0,
                result.returncode,
                _duration(start, self._clock()),
                prompt,
            )
        )
        return result


class ObservedTestCommandRunner:
    """Record one event around an existing target test-command runner."""

    __test__: ClassVar[bool] = False

    def __init__(
        self,
        delegate: TestCommandRunner,
        recorder: TelemetryRecorder,
        operation: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._operation = _operation(operation)
        self._clock = clock

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        """Delegate unchanged while recording no command arguments or output."""
        start = self._clock()
        try:
            result = self._delegate.run(command, cwd, timeout_seconds)
        except Exception:
            self._recorder.record(
                _event(
                    self._recorder.session_id,
                    self._operation,
                    "test",
                    command,
                    False,
                    None,
                    _duration(start, self._clock()),
                )
            )
            raise
        self._recorder.record(
            _event(
                self._recorder.session_id,
                self._operation,
                "test",
                command,
                result.returncode == 0,
                result.returncode,
                _duration(start, self._clock()),
            )
        )
        return result


def _metrics_path(
    root: Path,
    session_id: str,
    create: bool,
) -> Path:
    workspace = root / ".agent"
    directory = workspace / "metrics"
    if workspace.is_symlink() or directory.is_symlink():
        raise TelemetryError("Telemetry path is unsafe")
    try:
        if create:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise TelemetryError("Telemetry directory could not be prepared") from error
    path = directory / f"{_session_id(session_id)}.jsonl"
    if path.is_symlink():
        raise TelemetryError("Telemetry path is unsafe")
    return path


def _optional_nonnegative_int(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TelemetryError("Telemetry usage is invalid")
    return value


def _optional_nonnegative_number(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetryError("Telemetry cost is invalid")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise TelemetryError("Telemetry cost is invalid")
    return result


def _validate_event(value: object, session_id: str) -> Dict[str, object]:
    if not isinstance(value, dict) or set(value) != EVENT_FIELDS:
        raise TelemetryError("Telemetry event is invalid")
    event: Dict[str, object] = value
    returncode = event["returncode"]
    duration = event["duration_seconds"]
    prompt_version = event["prompt_version"]
    prompt_sha = event["prompt_sha256"]
    if (
        event["schema_version"] != SCHEMA_VERSION
        or event["session_id"] != session_id
        or not isinstance(event["operation"], str)
        or _operation(event["operation"]) != event["operation"]
        or event["kind"] not in {"model", "test"}
        or not isinstance(event["tool"], str)
        or TOOL_PATTERN.fullmatch(event["tool"]) is None
        or not isinstance(event["success"], bool)
        or (
            returncode is not None
            and (isinstance(returncode, bool) or not isinstance(returncode, int))
        )
        or (returncode is None and event["success"] is True)
        or (
            isinstance(returncode, int)
            and not isinstance(returncode, bool)
            and event["success"] is not (returncode == 0)
        )
        or isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or float(duration) < 0
        or not (
            (prompt_version is None and prompt_sha is None)
            or (
                isinstance(prompt_version, str)
                and 0 < len(prompt_version) <= 80
                and isinstance(prompt_sha, str)
                and SHA256_PATTERN.fullmatch(prompt_sha) is not None
            )
        )
    ):
        raise TelemetryError("Telemetry event is invalid")
    usage = (
        _optional_nonnegative_int(event["input_tokens"]),
        _optional_nonnegative_int(event["output_tokens"]),
        _optional_nonnegative_number(event["cost_usd"]),
    )
    if (
        event["usage_status"] not in {"reported", "unavailable"}
        or (
            event["usage_status"] == "unavailable"
            and any(item is not None for item in usage)
        )
        or (event["usage_status"] == "reported" and any(item is None for item in usage))
    ):
        raise TelemetryError("Telemetry usage is invalid")
    return event


def load_session_metrics(root: Path, session_id: str) -> SessionMetrics:
    """Strictly aggregate one Session's bounded append-only telemetry."""
    resolved_id = _session_id(session_id)
    path = _metrics_path(root.resolve(), resolved_id, create=False)
    if not path.exists():
        return SessionMetrics(resolved_id, 0, 0, 0, 0, 0.0, None, None, None)
    try:
        if path.stat().st_size > MAX_METRICS_BYTES:
            raise TelemetryError("Telemetry file is too large")
        lines = path.read_text(encoding="utf-8").splitlines()
        events = tuple(_validate_event(json.loads(line), resolved_id) for line in lines)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TelemetryError("Telemetry file is invalid") from error
    model_calls = sum(event["kind"] == "model" for event in events)
    test_calls = sum(event["kind"] == "test" for event in events)
    successful = sum(event["success"] is True for event in events)
    duration = round(
        sum(float(cast(float, event["duration_seconds"])) for event in events),
        6,
    )
    usage_complete = bool(events) and all(
        event["usage_status"] == "reported" for event in events
    )
    return SessionMetrics(
        resolved_id,
        len(events),
        model_calls,
        test_calls,
        successful,
        duration,
        sum(cast(int, event["input_tokens"]) for event in events)
        if usage_complete
        else None,
        sum(cast(int, event["output_tokens"]) for event in events)
        if usage_complete
        else None,
        round(sum(float(cast(float, event["cost_usd"])) for event in events), 6)
        if usage_complete
        else None,
    )


def render_session_metrics(metrics: SessionMetrics) -> str:
    """Render deterministic human-readable Session metrics."""
    rate = (
        f"{metrics.successful_calls / metrics.event_count:.2%}"
        if metrics.event_count
        else "n/a"
    )
    tokens = (
        str(metrics.input_tokens + metrics.output_tokens)
        if metrics.input_tokens is not None and metrics.output_tokens is not None
        else "unavailable"
    )
    cost = f"{metrics.cost_usd:.6f}" if metrics.cost_usd is not None else "unavailable"
    return (
        f"Session metrics: {metrics.session_id}\n"
        f"Calls: {metrics.event_count} ({metrics.successful_calls} successful, {rate})\n"
        f"Model calls: {metrics.model_calls}\n"
        f"Test calls: {metrics.test_calls}\n"
        f"Duration: {metrics.duration_seconds:.6f}s\n"
        f"Tokens: {tokens}\n"
        f"Cost USD: {cost}\n"
    )


def active_telemetry_recorder(root: Path) -> Optional[TelemetryRecorder]:
    """Return a recorder for the active Session, or None when none is active."""
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise TelemetryError(
            "Project status could not be read for telemetry"
        ) from error
    if status.current_session is None:
        return None
    return TelemetryRecorder(root, status.current_session)


def observe_process_runner(
    root: Path,
    operation: str,
    delegate: ProcessRunner,
) -> ProcessRunner:
    """Wrap a model runner only when an active Session exists."""
    recorder = active_telemetry_recorder(root)
    return (
        ObservedProcessRunner(delegate, recorder, operation)
        if recorder is not None
        else delegate
    )


def observe_test_runner(
    root: Path,
    operation: str,
    delegate: TestCommandRunner,
) -> TestCommandRunner:
    """Wrap a test runner only when an active Session exists."""
    recorder = active_telemetry_recorder(root)
    return (
        ObservedTestCommandRunner(delegate, recorder, operation)
        if recorder is not None
        else delegate
    )
