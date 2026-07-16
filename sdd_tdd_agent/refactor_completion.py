import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Tuple

from sdd_tdd_agent.cycle_completion import canonical_json_sha256
from sdd_tdd_agent.execution_config import (
    load_full_test_suite_timeout,
    load_test_command_timeout,
)
from sdd_tdd_agent.production_source_generation import production_source_path
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    MAX_EVIDENCE_STREAM_CHARACTERS,
    TestCommandProcessResult,
    TestCommandRunner,
    sanitize_test_evidence,
)


COMPLETION_FIELDS = {
    "completed_tests",
    "final_test",
    "green_evidence_sha256",
    "test_source_sha256",
    "production_source_sha256",
}
REVIEW_FIELDS = {"decision", "completion_sha256", "report_sha256"}
GREEN_FIELDS = {"test_id", "current_test", "full_suite"}
PROCESS_FIELDS = {"command", "returncode", "stdout", "stderr"}
ARTIFACT_FIELDS = {"test_id", "file_path", "sha256"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class RefactorVerificationError(RuntimeError):
    """Safe public error for failed final refactor verification."""


@dataclass(frozen=True)
class RefactorCompletionRun:
    """Result of final no-source-change verification and DONE transition."""

    __test__: ClassVar[bool] = False

    session_id: str
    completed_test_count: int


@dataclass(frozen=True)
class _Artifact:
    test_id: str
    file_path: str
    sha256: str


@dataclass(frozen=True)
class _RefactorContext:
    session_id: str
    state_path: Path
    raw_state: str
    state: Dict[str, object]
    completed_tests: Tuple[str, ...]
    current_command: Tuple[str, ...]
    suite_command: Tuple[str, ...]


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RefactorVerificationError(f"{label} could not be read") from error


def _state(raw: str) -> Dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RefactorVerificationError("Session state is invalid") from error
    if not isinstance(value, dict):
        raise RefactorVerificationError("Session state must be a JSON object")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise RefactorVerificationError(f"{label} digest is invalid")
    return value


def _artifact(value: object, final_test: str, label: str) -> _Artifact:
    if not isinstance(value, dict) or set(value) != ARTIFACT_FIELDS:
        raise RefactorVerificationError(f"{label} artifact is invalid")
    test_id = value["test_id"]
    file_path = value["file_path"]
    digest = value["sha256"]
    if (
        test_id != final_test
        or not isinstance(file_path, str)
        or not isinstance(digest, str)
        or SHA256_PATTERN.fullmatch(digest) is None
    ):
        raise RefactorVerificationError(f"{label} artifact is stale")
    return _Artifact(final_test, file_path, digest)


def _test_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or "\0" in normalized
        or path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] in {".agent", ".git"}
    ):
        raise RefactorVerificationError("Final test artifact path is unsafe")
    return path


def _file_digest(root: Path, relative: PurePosixPath, label: str) -> str:
    target = root.resolve()
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise RefactorVerificationError(f"{label} artifact changed")
    try:
        content = target.read_bytes()
    except OSError as error:
        raise RefactorVerificationError(
            f"{label} artifact could not be read"
        ) from error
    return hashlib.sha256(content).hexdigest()


def _validate_artifacts(
    root: Path,
    state: Dict[str, object],
    final_test: str,
    completion: Dict[str, object],
) -> None:
    test = _artifact(state.get("test_source"), final_test, "Final test")
    production = _artifact(
        state.get("production_source"),
        final_test,
        "Final production",
    )
    try:
        production_path = production_source_path(production.file_path)
    except ValueError as error:
        raise RefactorVerificationError(
            "Final production artifact path is unsafe"
        ) from error
    if (
        _file_digest(root, _test_path(test.file_path), "Final test") != test.sha256
        or _file_digest(root, production_path, "Final production") != production.sha256
        or completion["test_source_sha256"] != test.sha256
        or completion["production_source_sha256"] != production.sha256
    ):
        raise RefactorVerificationError("Final source artifact changed")


def _command_evidence(
    root: Path,
    value: object,
    label: str,
) -> Tuple[str, ...]:
    if not isinstance(value, dict) or set(value) != PROCESS_FIELDS:
        raise RefactorVerificationError(f"{label} GREEN evidence is invalid")
    command = value["command"]
    if (
        not isinstance(command, list)
        or not command
        or any(
            not isinstance(token, str) or not token.strip() or "\0" in token
            for token in command
        )
        or not isinstance(value["returncode"], int)
        or isinstance(value["returncode"], bool)
        or value["returncode"] != 0
    ):
        raise RefactorVerificationError(f"{label} recorded command is invalid")
    for stream_name in ("stdout", "stderr"):
        stream = value[stream_name]
        if (
            not isinstance(stream, str)
            or len(stream) > MAX_EVIDENCE_STREAM_CHARACTERS
            or sanitize_test_evidence(root, stream) != stream
        ):
            raise RefactorVerificationError(f"{label} GREEN evidence is invalid")
    return tuple(command)


def _validate_audit_chain(
    root: Path,
    session: Path,
    state: Dict[str, object],
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    completion = state.get("implementation_completion")
    review = state.get("implementation_review")
    evidence = state.get("green_evidence")
    if not isinstance(completion, dict) or set(completion) != COMPLETION_FIELDS:
        raise RefactorVerificationError("Implementation completion is invalid")
    if not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
        raise RefactorVerificationError("Implementation review is invalid")
    if not isinstance(evidence, dict) or set(evidence) != GREEN_FIELDS:
        raise RefactorVerificationError("Final GREEN evidence is invalid")
    completed_value = completion["completed_tests"]
    final_test = completion["final_test"]
    if (
        not isinstance(completed_value, list)
        or not completed_value
        or any(not isinstance(test_id, str) for test_id in completed_value)
        or not isinstance(final_test, str)
        or final_test != completed_value[-1]
        or evidence["test_id"] != final_test
    ):
        raise RefactorVerificationError("Implementation completion is stale")
    evidence_sha = _digest(
        completion["green_evidence_sha256"],
        "GREEN evidence",
    )
    if canonical_json_sha256(evidence) != evidence_sha:
        raise RefactorVerificationError("Implementation completion is stale")
    completion_sha = canonical_json_sha256(completion)
    if (
        review["decision"] != "invariant_review_passed"
        or review["completion_sha256"] != completion_sha
    ):
        raise RefactorVerificationError("Implementation review is stale")
    report_sha = _digest(review["report_sha256"], "Review report")
    report_path = session / "review.md"
    if report_path.is_symlink():
        raise RefactorVerificationError("Review report changed")
    report = _read_text(report_path, "Review report")
    if hashlib.sha256(report.encode("utf-8")).hexdigest() != report_sha:
        raise RefactorVerificationError("Review report changed")
    _validate_artifacts(root, state, final_test, completion)
    return (
        tuple(completed_value),
        _command_evidence(root, evidence["current_test"], "Current test"),
        _command_evidence(root, evidence["full_suite"], "Full suite"),
    )


def _load_context(root: Path, session_id: str) -> _RefactorContext:
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    raw_state = _read_text(state_path, "Session state")
    state = _state(raw_state)
    if state.get("session_id") != session_id:
        raise RefactorVerificationError("Session state identifier is invalid")
    if state.get("state") != "REFACTOR":
        raise RefactorVerificationError("Final verification requires REFACTOR state")
    completed, current, suite = _validate_audit_chain(root, session, state)
    if _read_text(state_path, "Session state") != raw_state:
        raise RefactorVerificationError("Session state changed concurrently")
    return _RefactorContext(
        session_id,
        state_path,
        raw_state,
        state,
        completed,
        current,
        suite,
    )


def _revalidate(root: Path, before: _RefactorContext) -> _RefactorContext:
    after = _load_context(root, before.session_id)
    if after.raw_state != before.raw_state:
        raise RefactorVerificationError("Session state changed concurrently")
    return after


def _result_evidence(
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


def _write_done(
    root: Path,
    context: _RefactorContext,
    current_result: TestCommandProcessResult,
    suite_result: TestCommandProcessResult,
) -> None:
    context.state["state"] = "DONE"
    context.state["refactor"] = {
        "mode": "no_source_change",
        "decision": "verified",
    }
    context.state["final_verification"] = {
        "current_test": _result_evidence(
            root,
            context.current_command,
            current_result,
        ),
        "full_suite": _result_evidence(
            root,
            context.suite_command,
            suite_result,
        ),
    }
    if _read_text(context.state_path, "Session state") != context.raw_state:
        raise RefactorVerificationError("Session state changed concurrently")
    temporary = context.state_path.with_name(".state.json.refactor.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(context.state, indent=2)}\n")
        temporary.replace(context.state_path)
    except FileExistsError as error:
        raise RefactorVerificationError(
            "Refactor verification update is already in progress"
        ) from error
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise RefactorVerificationError(
            "Refactor verification state could not be updated"
        ) from error


def complete_active_refactor(
    root: Path,
    runner: TestCommandRunner,
) -> RefactorCompletionRun:
    """Run final no-source-change verification and atomically enter DONE."""
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise RefactorVerificationError("Project status could not be read") from error
    if status.current_session is None:
        raise RefactorVerificationError("Project has no active Session")
    before = _load_context(root, status.current_session)
    current_timeout = load_test_command_timeout(root)
    suite_timeout = load_full_test_suite_timeout(root)
    current_result = runner.run(
        before.current_command,
        root.resolve(),
        current_timeout,
    )
    if current_result.returncode != 0:
        raise RefactorVerificationError("Current test failed after refactor")
    after_current = _revalidate(root, before)
    suite_result = runner.run(
        after_current.suite_command,
        root.resolve(),
        suite_timeout,
    )
    if suite_result.returncode != 0:
        raise RefactorVerificationError("Full test suite failed after refactor")
    after_suite = _revalidate(root, after_current)
    _write_done(root, after_suite, current_result, suite_result)
    return RefactorCompletionRun(
        status.current_session,
        len(after_suite.completed_tests),
    )
