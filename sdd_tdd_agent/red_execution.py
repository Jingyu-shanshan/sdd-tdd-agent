import hashlib
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Protocol, Tuple

from sdd_tdd_agent.tdd_cycle import load_current_test_case
from sdd_tdd_agent.test_execution import detect_test_command
from sdd_tdd_agent.test_generation import TestCasePlan
from sdd_tdd_agent.test_source_generation import GeneratedTestSource


MAX_EVIDENCE_STREAM_CHARACTERS = 16_000
ARTIFACT_FIELDS = {"test_id", "file_path", "sha256"}
INVALID_FAILURE_MARKERS = (
    "no tests found",
    "no test found",
    "no matching tests",
    "no matching test",
    "could not find any tests",
    "test file not found",
    "no tests were executed",
    "no tests to run",
    "unknown option",
    "unrecognized option",
    "unknown command",
    "invalid option",
)
ANSI_PATTERN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
SECRET_PATTERN = re.compile(r"(?i)\b(token|password|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)")
AUTHORIZATION_PATTERN = re.compile(r"(?i)\bauthorization\s*:\s*[^\r\n]+")
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class RedExecutionError(RuntimeError):
    """Safe public error for an untrusted or failed RED execution."""


@dataclass(frozen=True)
class TestCommandProcessResult:
    """Captured result for one shell-free test command."""

    __test__: ClassVar[bool] = False

    returncode: int
    stdout: str
    stderr: str


class TestCommandRunner(Protocol):
    """Typed and mockable boundary for executing one current test."""

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        """Execute an already-tokenized command without a shell."""
        ...


class SystemTestCommandRunner:
    """Production runner for one tokenized test command."""

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        """Run one command from the explicit project root."""
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RedExecutionError("Test command timed out") from error
        except OSError as error:
            raise RedExecutionError("Test command could not be started") from error
        return TestCommandProcessResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )


@dataclass(frozen=True)
class TestSourceArtifact:
    """Digest-bound identity for the generated current test source."""

    __test__: ClassVar[bool] = False

    test_id: str
    file_path: str
    sha256: str


@dataclass(frozen=True)
class RedExecutionRun:
    """Result of recording a trustworthy current-test RED failure."""

    __test__: ClassVar[bool] = False

    session_id: str
    test_id: str
    file_path: str
    command: Tuple[str, ...]
    returncode: int


@dataclass(frozen=True)
class _ArtifactContext:
    state_path: Path
    raw_state: str
    state: Dict[str, object]
    case: TestCasePlan
    artifact: TestSourceArtifact


def _state_path(root: Path, session_id: str) -> Path:
    if SESSION_ID_PATTERN.fullmatch(session_id) is None:
        raise RedExecutionError("Invalid Session identifier")
    return root / ".agent" / "sessions" / session_id / "state.json"


def _read_state_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RedExecutionError("Session state could not be read") from error


def _target(root: Path, file_path: str) -> Path:
    relative = PurePosixPath(file_path.replace("\\", "/"))
    project = root.resolve()
    current = project
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RedExecutionError("Generated test source changed after writing")
    return current


def _digest_target(root: Path, file_path: str) -> str:
    target = _target(root, file_path)
    try:
        content = target.read_bytes()
    except OSError as error:
        raise RedExecutionError(
            "Generated test source could not be verified"
        ) from error
    return hashlib.sha256(content).hexdigest()


def _load_state(path: Path, raw: str) -> Dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RedExecutionError("Session state is invalid") from error
    if not isinstance(value, dict):
        raise RedExecutionError("Session state must be a JSON object")
    return value


def _write_state_atomically(
    path: Path,
    state: Dict[str, object],
    temporary_name: str,
) -> None:
    temporary = path.with_name(temporary_name)
    serialized = f"{json.dumps(state, indent=2)}\n"
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(serialized)
        temporary.replace(path)
    except FileExistsError as error:
        raise RedExecutionError(
            "Session state update is already in progress"
        ) from error
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise RedExecutionError("Session state could not be updated") from error


def record_test_source_artifact(
    root: Path,
    session_id: str,
    generated: GeneratedTestSource,
) -> TestSourceArtifact:
    """Bind the current WRITE_TEST state to the exact generated file digest."""
    state_path = _state_path(root, session_id)
    raw_state = _read_state_text(state_path)
    case = load_current_test_case(root, session_id, "WRITE_TEST")
    if _read_state_text(state_path) != raw_state:
        raise RedExecutionError("Session state changed concurrently")
    if (
        not isinstance(generated, GeneratedTestSource)
        or generated.test_id != case.test_id
        or generated.file_path.replace("\\", "/") != case.test_file.replace("\\", "/")
    ):
        raise RedExecutionError("Generated test source does not match current test")
    target = _target(root, generated.file_path)
    try:
        actual_content = target.read_bytes()
    except OSError as error:
        raise RedExecutionError(
            "Generated test source could not be verified"
        ) from error
    if actual_content != generated.content.encode("utf-8"):
        raise RedExecutionError("Generated test source changed after writing")
    artifact = TestSourceArtifact(
        case.test_id,
        case.test_file.replace("\\", "/"),
        hashlib.sha256(actual_content).hexdigest(),
    )
    if _read_state_text(state_path) != raw_state:
        raise RedExecutionError("Session state changed concurrently")
    state = _load_state(state_path, raw_state)
    state["test_source"] = {
        "test_id": artifact.test_id,
        "file_path": artifact.file_path,
        "sha256": artifact.sha256,
    }
    state.pop("red_evidence", None)
    _write_state_atomically(state_path, state, ".state.json.test-source.tmp")
    return artifact


def _artifact_from_state(value: object) -> TestSourceArtifact:
    if not isinstance(value, dict) or set(value) != ARTIFACT_FIELDS:
        raise RedExecutionError("Generated test source record is invalid")
    test_id = value["test_id"]
    file_path = value["file_path"]
    digest = value["sha256"]
    if (
        not isinstance(test_id, str)
        or not isinstance(file_path, str)
        or not isinstance(digest, str)
        or SHA256_PATTERN.fullmatch(digest) is None
    ):
        raise RedExecutionError("Generated test source record is invalid")
    return TestSourceArtifact(test_id, file_path, digest)


def _validate_artifact(
    root: Path,
    session_id: str,
    expected_phase: str,
) -> _ArtifactContext:
    state_path = _state_path(root, session_id)
    raw_state = _read_state_text(state_path)
    case = load_current_test_case(root, session_id, expected_phase)
    if _read_state_text(state_path) != raw_state:
        raise RedExecutionError("Session state changed concurrently")
    state = _load_state(state_path, raw_state)
    artifact = _artifact_from_state(state.get("test_source"))
    if artifact.test_id != case.test_id or artifact.file_path.replace(
        "\\", "/"
    ) != case.test_file.replace("\\", "/"):
        raise RedExecutionError("Generated test source record is stale")
    if _digest_target(root, artifact.file_path) != artifact.sha256:
        raise RedExecutionError("Generated test source changed after writing")
    return _ArtifactContext(state_path, raw_state, state, case, artifact)


def is_current_test_source_recorded(root: Path, session_id: str) -> bool:
    """Return whether a valid digest-bound source record exists for WRITE_TEST."""
    state_path = _state_path(root, session_id)
    raw_state = _read_state_text(state_path)
    state = _load_state(state_path, raw_state)
    if "test_source" not in state:
        return False
    _validate_artifact(root, session_id, "WRITE_TEST")
    return True


def has_test_source_artifact_record(root: Path, session_id: str) -> bool:
    """Return whether Session state contains any test-source artifact record."""
    state_path = _state_path(root, session_id)
    state = _load_state(state_path, _read_state_text(state_path))
    return "test_source" in state


def validate_current_test_source_artifact(
    root: Path,
    session_id: str,
    expected_phase: str,
) -> TestSourceArtifact:
    """Validate and return the digest-bound current test source artifact."""
    return _validate_artifact(root, session_id, expected_phase).artifact


def _has_current_identity(output: str, case: TestCasePlan) -> bool:
    normalized = output.replace("\\", "/")
    path = PurePosixPath(case.test_file.replace("\\", "/"))
    identities = (
        case.test_file.replace("\\", "/"),
        path.name,
        path.stem,
        case.test_name,
    )
    return any(identity and identity in normalized for identity in identities)


def _validate_process_failure(result: TestCommandProcessResult) -> str:
    if result.returncode == 0:
        raise RedExecutionError("Test command did not fail")
    if result.returncode < 0:
        raise RedExecutionError("Test command was terminated by a signal")
    output = f"{result.stdout}\n{result.stderr}"
    folded = output.casefold()
    if any(marker in folded for marker in INVALID_FAILURE_MARKERS):
        raise RedExecutionError("Test command did not execute tests")
    if not output.strip():
        raise RedExecutionError("Test command failure output is empty")
    return output


def validate_current_test_failure(
    result: TestCommandProcessResult,
    case: TestCasePlan,
) -> None:
    """Reject a failure that cannot be attributed to the current test."""
    output = _validate_process_failure(result)
    if not _has_current_identity(output, case):
        raise RedExecutionError("Test failure could not be attributed to current test")


def validate_test_suite_failure(result: TestCommandProcessResult) -> None:
    """Reject a full-suite failure that lacks trustworthy test execution evidence."""
    _validate_process_failure(result)


def _remove_control_characters(value: str) -> str:
    return "".join(
        character
        for character in value
        if character in {"\n", "\t"} or ord(character) >= 32
    )


def sanitize_test_evidence(root: Path, value: str) -> str:
    """Remove sensitive and unsafe content from one persisted test stream."""
    sanitized = ANSI_PATTERN.sub("", value)
    sanitized = _remove_control_characters(sanitized)
    resolved = str(root.resolve())
    sanitized = sanitized.replace(resolved, "<PROJECT_ROOT>")
    sanitized = AUTHORIZATION_PATTERN.sub("Authorization: <REDACTED>", sanitized)
    sanitized = BEARER_PATTERN.sub("Bearer <REDACTED>", sanitized)
    sanitized = SECRET_PATTERN.sub(r"\1\2<REDACTED>", sanitized)
    return sanitized[:MAX_EVIDENCE_STREAM_CHARACTERS]


def execute_current_test_for_red(
    root: Path,
    session_id: str,
    runner: TestCommandRunner,
    timeout_seconds: float,
) -> RedExecutionRun:
    """Execute one digest-bound current test and atomically record trusted RED."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise RedExecutionError("Test command timeout must be positive and finite")
    before = _validate_artifact(root, session_id, "WRITE_TEST")
    plan = detect_test_command(root, before.case)
    result = runner.run(plan.command, root.resolve(), timeout_seconds)
    validate_current_test_failure(result, before.case)
    after = _validate_artifact(root, session_id, "WRITE_TEST")
    if after.raw_state != before.raw_state:
        raise RedExecutionError("Session state changed concurrently")
    progress = after.state.get("tdd_cycle")
    if not isinstance(progress, dict):
        raise RedExecutionError("TDD cycle progress is invalid")
    progress["phase"] = "RED"
    after.state["red_evidence"] = {
        "test_id": after.case.test_id,
        "file_path": after.case.test_file,
        "command": list(plan.command),
        "returncode": result.returncode,
        "stdout": sanitize_test_evidence(root, result.stdout),
        "stderr": sanitize_test_evidence(root, result.stderr),
    }
    if _read_state_text(after.state_path) != after.raw_state:
        raise RedExecutionError("Session state changed concurrently")
    _write_state_atomically(
        after.state_path,
        after.state,
        ".state.json.red-execution.tmp",
    )
    return RedExecutionRun(
        session_id,
        after.case.test_id,
        after.case.test_file,
        plan.command,
        result.returncode,
    )
