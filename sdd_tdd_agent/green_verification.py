import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Tuple

from sdd_tdd_agent.execution_config import (
    load_full_test_suite_timeout,
    load_test_command_timeout,
)
from sdd_tdd_agent.production_source_generation import production_source_path
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    TestCommandProcessResult,
    TestCommandRunner,
    sanitize_test_evidence,
    validate_current_test_failure,
    validate_current_test_source_artifact,
    validate_test_suite_failure,
)
from sdd_tdd_agent.tdd_cycle import load_current_test_case
from sdd_tdd_agent.test_execution import (
    detect_full_test_command,
    detect_test_command,
)
from sdd_tdd_agent.test_generation import TestCasePlan


ARTIFACT_FIELDS = {"test_id", "file_path", "sha256"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class GreenVerificationError(RuntimeError):
    """Safe public error for a failed or concurrent GREEN verification."""


@dataclass(frozen=True)
class ProductionSourceArtifact:
    """Digest-bound production source generated for the current test."""

    __test__: ClassVar[bool] = False

    test_id: str
    file_path: str
    sha256: str


@dataclass(frozen=True)
class GreenVerificationRun:
    """Result of passing the current test and complete test suite."""

    __test__: ClassVar[bool] = False

    session_id: str
    test_id: str
    current_command: Tuple[str, ...]
    full_suite_command: Tuple[str, ...]


@dataclass(frozen=True)
class _VerificationContext:
    session_id: str
    state_path: Path
    raw_state: str
    state: Dict[str, object]
    case: TestCasePlan
    production_source: ProductionSourceArtifact


def _read_state(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise GreenVerificationError("Session state could not be read") from error


def _parse_state(raw: str) -> Dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise GreenVerificationError("Session state is invalid") from error
    if not isinstance(value, dict):
        raise GreenVerificationError("Session state must be a JSON object")
    return value


def _production_artifact(value: object) -> ProductionSourceArtifact:
    if not isinstance(value, dict) or set(value) != ARTIFACT_FIELDS:
        raise GreenVerificationError("Production source record is invalid")
    test_id = value["test_id"]
    file_path = value["file_path"]
    digest = value["sha256"]
    if (
        not isinstance(test_id, str)
        or not isinstance(file_path, str)
        or not isinstance(digest, str)
        or SHA256_PATTERN.fullmatch(digest) is None
    ):
        raise GreenVerificationError("Production source record is invalid")
    return ProductionSourceArtifact(test_id, file_path, digest)


def _production_digest(root: Path, artifact: ProductionSourceArtifact) -> str:
    try:
        relative = production_source_path(artifact.file_path)
    except ValueError as error:
        raise GreenVerificationError("Production source record is invalid") from error
    target = root.resolve()
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise GreenVerificationError("Production source changed after writing")
    try:
        content = target.read_bytes()
    except OSError as error:
        raise GreenVerificationError(
            "Production source could not be verified"
        ) from error
    return hashlib.sha256(content).hexdigest()


def _load_context(
    root: Path,
    session_id: str,
) -> _VerificationContext:
    if SESSION_ID_PATTERN.fullmatch(session_id) is None:
        raise GreenVerificationError("Invalid Session identifier")
    state_path = root / ".agent" / "sessions" / session_id / "state.json"
    raw_state = _read_state(state_path)
    state = _parse_state(raw_state)
    try:
        case = load_current_test_case(root, session_id, "IMPLEMENT")
        validate_current_test_source_artifact(root, session_id, "IMPLEMENT")
    except (ValueError, RedExecutionError) as error:
        raise GreenVerificationError(str(error)) from error
    if _read_state(state_path) != raw_state:
        raise GreenVerificationError("Session state changed concurrently")
    artifact = _production_artifact(state.get("production_source"))
    if artifact.test_id != case.test_id:
        raise GreenVerificationError("Production source record is stale")
    if _production_digest(root, artifact) != artifact.sha256:
        raise GreenVerificationError("Production source changed after writing")
    if _read_state(state_path) != raw_state:
        raise GreenVerificationError("Session state changed concurrently")
    return _VerificationContext(
        session_id,
        state_path,
        raw_state,
        state,
        case,
        artifact,
    )


def _revalidate(root: Path, before: _VerificationContext) -> _VerificationContext:
    after = _load_context(root, before.session_id)
    if after.raw_state != before.raw_state:
        raise GreenVerificationError("Session state changed concurrently")
    return after


def _evidence(
    root: Path,
    command: Tuple[str, ...],
    result: TestCommandProcessResult,
) -> Dict[str, object]:
    return {
        "command": list(command),
        "returncode": result.returncode,
        "stdout": sanitize_test_evidence(root, result.stdout),
        "stderr": sanitize_test_evidence(root, result.stderr),
    }


def _write_state(
    context: _VerificationContext,
    state: Dict[str, object],
) -> None:
    if _read_state(context.state_path) != context.raw_state:
        raise GreenVerificationError("Session state changed concurrently")
    temporary = context.state_path.with_name(".state.json.green-verification.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(state, indent=2)}\n")
        temporary.replace(context.state_path)
    except FileExistsError as error:
        raise GreenVerificationError(
            "Session state update is already in progress"
        ) from error
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise GreenVerificationError("Session state could not be updated") from error


def _return_to_red(
    root: Path,
    context: _VerificationContext,
    command: Tuple[str, ...],
    result: TestCommandProcessResult,
    stage: str,
) -> None:
    progress = context.state.get("tdd_cycle")
    if not isinstance(progress, dict):
        raise GreenVerificationError("TDD cycle progress is invalid")
    progress["phase"] = "RED"
    context.state["red_evidence"] = {
        "test_id": context.case.test_id,
        "file_path": context.case.test_file,
        **_evidence(root, command, result),
    }
    context.state["verification_failure"] = {"stage": stage}
    context.state.pop("green_evidence", None)
    _write_state(context, context.state)


def _record_green(
    root: Path,
    context: _VerificationContext,
    current_command: Tuple[str, ...],
    current_result: TestCommandProcessResult,
    suite_command: Tuple[str, ...],
    suite_result: TestCommandProcessResult,
) -> None:
    progress = context.state.get("tdd_cycle")
    if not isinstance(progress, dict):
        raise GreenVerificationError("TDD cycle progress is invalid")
    completed = progress.get("completed_tests")
    if not isinstance(completed, list):
        raise GreenVerificationError("TDD cycle progress is invalid")
    progress["phase"] = "GREEN"
    completed.append(context.case.test_id)
    context.state["green_evidence"] = {
        "test_id": context.case.test_id,
        "current_test": _evidence(root, current_command, current_result),
        "full_suite": _evidence(root, suite_command, suite_result),
    }
    context.state.pop("verification_failure", None)
    _write_state(context, context.state)


def verify_active_implementation(
    root: Path,
    runner: TestCommandRunner,
) -> GreenVerificationRun:
    """Verify one digest-bound implementation through current and full tests."""
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise GreenVerificationError("Session state could not be read") from error
    if status.current_session is None:
        raise GreenVerificationError("Project has no active Session")
    session_id = status.current_session
    before = _load_context(root, session_id)
    current = detect_test_command(root, before.case)
    suite = detect_full_test_command(root, before.case)
    current_timeout = load_test_command_timeout(root)
    suite_timeout = load_full_test_suite_timeout(root)

    current_result = runner.run(current.command, root.resolve(), current_timeout)
    if current_result.returncode != 0:
        validate_current_test_failure(current_result, before.case)
        after_current = _revalidate(root, before)
        _return_to_red(
            root,
            after_current,
            current.command,
            current_result,
            "current_test",
        )
        raise GreenVerificationError("Current test remains RED after implementation")

    after_current = _revalidate(root, before)
    suite_result = runner.run(suite.command, root.resolve(), suite_timeout)
    if suite_result.returncode != 0:
        validate_test_suite_failure(suite_result)
        after_suite = _revalidate(root, after_current)
        _return_to_red(
            root,
            after_suite,
            suite.command,
            suite_result,
            "full_suite",
        )
        raise GreenVerificationError("Full test suite failed; cycle returned to RED")

    after_suite = _revalidate(root, after_current)
    _record_green(
        root,
        after_suite,
        current.command,
        current_result,
        suite.command,
        suite_result,
    )
    return GreenVerificationRun(
        session_id,
        before.case.test_id,
        current.command,
        suite.command,
    )
