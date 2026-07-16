import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Tuple

from sdd_tdd_agent.green_verification import (
    GreenVerificationError,
    validate_production_source_artifact,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    MAX_EVIDENCE_STREAM_CHARACTERS,
    RedExecutionError,
    sanitize_test_evidence,
    validate_current_test_source_artifact,
)
from sdd_tdd_agent.tdd_cycle import (
    load_completed_test_ids,
    load_current_test_case,
    select_next_test_case,
)
from sdd_tdd_agent.test_execution import (
    detect_full_test_command,
    detect_test_command,
)
from sdd_tdd_agent.test_generation import TestCasePlan


GREEN_EVIDENCE_FIELDS = {"test_id", "current_test", "full_suite"}
PROCESS_EVIDENCE_FIELDS = {"command", "returncode", "stdout", "stderr"}
SHA256_LENGTH = 64


class CycleCompletionError(RuntimeError):
    """Safe public error for an invalid implementation completion."""


@dataclass(frozen=True)
class ImplementationCompletionRun:
    """Result of moving an exhausted GREEN test plan into REVIEW."""

    __test__: ClassVar[bool] = False

    session_id: str
    test_id: str
    completed_tests: Tuple[str, ...]


@dataclass(frozen=True)
class _CompletionContext:
    state_path: Path
    raw_state: str
    state: Dict[str, object]
    case: TestCasePlan
    completed_tests: Tuple[str, ...]


def _read_state(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CycleCompletionError("Session state could not be read") from error


def _parse_state(raw: str) -> Dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CycleCompletionError("Session state is invalid") from error
    if not isinstance(value, dict):
        raise CycleCompletionError("Session state must be a JSON object")
    return value


def _stream(root: Path, value: object) -> str:
    if not isinstance(value, str) or len(value) > MAX_EVIDENCE_STREAM_CHARACTERS:
        raise CycleCompletionError("GREEN evidence stream is invalid")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise CycleCompletionError("GREEN evidence stream is invalid") from error
    if sanitize_test_evidence(root, value) != value:
        raise CycleCompletionError("GREEN evidence stream is not sanitized")
    return value


def _process_evidence(
    root: Path,
    value: object,
    expected_command: Tuple[str, ...],
) -> None:
    if not isinstance(value, dict) or set(value) != PROCESS_EVIDENCE_FIELDS:
        raise CycleCompletionError("GREEN evidence process result is invalid")
    command = value["command"]
    returncode = value["returncode"]
    if (
        not isinstance(command, list)
        or tuple(command) != expected_command
        or any(
            not isinstance(token, str) or not token.strip() or "\0" in token
            for token in command
        )
        or isinstance(returncode, bool)
        or returncode != 0
    ):
        raise CycleCompletionError("GREEN evidence process result is invalid")
    _stream(root, value["stdout"])
    _stream(root, value["stderr"])


def _validate_green_evidence(
    root: Path,
    state: Dict[str, object],
    case: TestCasePlan,
) -> None:
    evidence = state.get("green_evidence")
    if not isinstance(evidence, dict) or set(evidence) != GREEN_EVIDENCE_FIELDS:
        raise CycleCompletionError("GREEN evidence is invalid")
    if evidence["test_id"] != case.test_id:
        raise CycleCompletionError("GREEN evidence is stale")
    current = detect_test_command(root, case)
    suite = detect_full_test_command(root, case)
    _process_evidence(root, evidence["current_test"], current.command)
    _process_evidence(root, evidence["full_suite"], suite.command)


def canonical_json_sha256(value: object) -> str:
    """Return a deterministic SHA-256 for one JSON-compatible value."""
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _artifact_digest(state: Dict[str, object], key: str) -> str:
    artifact = state.get(key)
    if not isinstance(artifact, dict):
        raise CycleCompletionError("Completion artifact record is invalid")
    digest = artifact.get("sha256")
    if not isinstance(digest, str) or len(digest) != SHA256_LENGTH:
        raise CycleCompletionError("Completion artifact record is invalid")
    return digest


def _completion_record(context: _CompletionContext) -> Dict[str, object]:
    evidence = context.state.get("green_evidence")
    return {
        "completed_tests": list(context.completed_tests),
        "final_test": context.case.test_id,
        "green_evidence_sha256": canonical_json_sha256(evidence),
        "test_source_sha256": _artifact_digest(context.state, "test_source"),
        "production_source_sha256": _artifact_digest(
            context.state,
            "production_source",
        ),
    }


def _load_context(root: Path, session_id: str) -> _CompletionContext:
    state_path = root / ".agent" / "sessions" / session_id / "state.json"
    raw_state = _read_state(state_path)
    state = _parse_state(raw_state)
    try:
        case = load_current_test_case(root, session_id, "GREEN")
        validate_current_test_source_artifact(root, session_id, "GREEN")
        validate_production_source_artifact(root, session_id, "GREEN")
        completed = load_completed_test_ids(root, session_id)
        remaining = select_next_test_case(root, session_id)
    except (GreenVerificationError, RedExecutionError, ValueError) as error:
        raise CycleCompletionError(str(error)) from error
    if remaining is not None:
        raise CycleCompletionError("Planned tests remain incomplete")
    if _read_state(state_path) != raw_state:
        raise CycleCompletionError("Session state changed concurrently")
    _validate_green_evidence(root, state, case)
    return _CompletionContext(
        state_path,
        raw_state,
        state,
        case,
        completed,
    )


def _write_state(context: _CompletionContext) -> None:
    if _read_state(context.state_path) != context.raw_state:
        raise CycleCompletionError("Session state changed concurrently")
    temporary = context.state_path.with_name(".state.json.cycle-completion.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(context.state, indent=2)}\n")
        temporary.replace(context.state_path)
    except FileExistsError as error:
        raise CycleCompletionError(
            "Session state update is already in progress"
        ) from error
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise CycleCompletionError("Session state could not be updated") from error


def complete_active_implementation(root: Path) -> ImplementationCompletionRun:
    """Atomically move an exhausted, trustworthy GREEN plan into REVIEW."""
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise CycleCompletionError("Project status could not be read") from error
    if status.current_session is None:
        raise CycleCompletionError("Project has no active Session")
    context = _load_context(root, status.current_session)
    after = _load_context(root, status.current_session)
    if after.raw_state != context.raw_state:
        raise CycleCompletionError("Session state changed concurrently")
    after.state["state"] = "REVIEW"
    after.state["current_task"] = None
    after.state["implementation_completion"] = _completion_record(after)
    _write_state(after)
    return ImplementationCompletionRun(
        status.current_session,
        after.case.test_id,
        after.completed_tests,
    )
