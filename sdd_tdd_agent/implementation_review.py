import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Tuple

from sdd_tdd_agent.cycle_completion import canonical_json_sha256
from sdd_tdd_agent.project_status import load_project_status


COMPLETION_FIELDS = {
    "completed_tests",
    "final_test",
    "green_evidence_sha256",
    "test_source_sha256",
    "production_source_sha256",
}
PROGRESS_FIELDS = {"current_test", "phase", "completed_tests"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PENDING_REVIEW = "# Review\n\nPending requirement analysis.\n"
MAX_REVIEW_CHARACTERS = 20_000


class ImplementationReviewError(RuntimeError):
    """Safe public error for an invalid implementation-review transition."""


@dataclass(frozen=True)
class ImplementationReviewRun:
    """Result of a deterministic implementation audit-integrity review."""

    __test__: ClassVar[bool] = False

    session_id: str
    final_test_id: str
    completed_test_count: int
    completion_sha256: str
    report_sha256: str


@dataclass(frozen=True)
class _ReviewContext:
    session_id: str
    state_path: Path
    raw_state: str
    state: Dict[str, object]
    review_path: Path
    raw_review: str
    final_test_id: str
    completed_tests: Tuple[str, ...]
    completion_sha256: str


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ImplementationReviewError(f"{label} could not be read") from error


def _state(raw: str) -> Dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ImplementationReviewError("Session state is invalid") from error
    if not isinstance(value, dict):
        raise ImplementationReviewError("Session state must be a JSON object")
    return value


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ImplementationReviewError(f"Implementation completion {label} is invalid")
    return value


def _artifact_sha(state: Dict[str, object], key: str) -> str:
    artifact = state.get(key)
    if not isinstance(artifact, dict):
        raise ImplementationReviewError("Implementation completion is stale")
    digest = artifact.get("sha256")
    if not isinstance(digest, str):
        raise ImplementationReviewError("Implementation completion is stale")
    return digest


def _completion(
    state: Dict[str, object],
) -> Tuple[str, Tuple[str, ...], str]:
    value = state.get("implementation_completion")
    if not isinstance(value, dict) or set(value) != COMPLETION_FIELDS:
        raise ImplementationReviewError("Implementation completion is invalid")
    completed_value = value["completed_tests"]
    final_test = value["final_test"]
    if (
        not isinstance(completed_value, list)
        or not completed_value
        or any(not isinstance(test_id, str) for test_id in completed_value)
        or len(set(completed_value)) != len(completed_value)
        or not isinstance(final_test, str)
        or final_test != completed_value[-1]
    ):
        raise ImplementationReviewError("Implementation completion is invalid")
    completed = tuple(completed_value)
    evidence_sha = _sha(value["green_evidence_sha256"], "evidence digest")
    test_sha = _sha(value["test_source_sha256"], "test digest")
    production_sha = _sha(value["production_source_sha256"], "source digest")
    if (
        canonical_json_sha256(state.get("green_evidence")) != evidence_sha
        or _artifact_sha(state, "test_source") != test_sha
        or _artifact_sha(state, "production_source") != production_sha
    ):
        raise ImplementationReviewError("Implementation completion is stale")
    return final_test, completed, canonical_json_sha256(value)


def _validate_progress(
    state: Dict[str, object],
    final_test: str,
    completed: Tuple[str, ...],
) -> None:
    progress = state.get("tdd_cycle")
    if not isinstance(progress, dict) or set(progress) != PROGRESS_FIELDS:
        raise ImplementationReviewError("Implementation completion progress is invalid")
    if (
        progress["current_test"] != final_test
        or progress["phase"] != "GREEN"
        or progress["completed_tests"] != list(completed)
    ):
        raise ImplementationReviewError("Implementation completion progress is stale")


def _load_context(root: Path, session_id: str) -> _ReviewContext:
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    raw_state = _read_text(state_path, "Session state")
    state = _state(raw_state)
    if state.get("session_id") != session_id:
        raise ImplementationReviewError("Session state identifier is invalid")
    if state.get("state") != "REVIEW":
        raise ImplementationReviewError("Implementation review requires REVIEW state")
    final_test, completed, completion_sha = _completion(state)
    _validate_progress(state, final_test, completed)
    review_path = session / "review.md"
    if review_path.is_symlink():
        raise ImplementationReviewError("Review artifact must not be a symbolic link")
    raw_review = _read_text(review_path, "Review artifact")
    if len(raw_review) > MAX_REVIEW_CHARACTERS:
        raise ImplementationReviewError("Review artifact is too large")
    return _ReviewContext(
        session_id,
        state_path,
        raw_state,
        state,
        review_path,
        raw_review,
        final_test,
        completed,
        completion_sha,
    )


def _render_report(context: _ReviewContext) -> str:
    return (
        "# Implementation Review\n\n"
        "## Result\n\n"
        "- Audit integrity: passed\n"
        f"- Completed tests: {len(context.completed_tests)}\n"
        f"- Final test: `{context.final_test_id}`\n"
        f"- Completion snapshot: `{context.completion_sha256}`\n\n"
        "## Scope\n\n"
        "- Semantic automated review: deferred to v0.3\n"
        "- Source code and process output are not stored in this report.\n"
        "- Final behavior-preserving verification is required in REFACTOR.\n"
    )


def _write_review(context: _ReviewContext, report: str) -> None:
    if context.raw_review not in {PENDING_REVIEW, report}:
        raise ImplementationReviewError("Review artifact contains unrecognized content")
    report_sha = hashlib.sha256(report.encode("utf-8")).hexdigest()
    context.state["state"] = "REFACTOR"
    context.state["implementation_review"] = {
        "decision": "invariant_review_passed",
        "completion_sha256": context.completion_sha256,
        "report_sha256": report_sha,
    }
    review_temporary = context.review_path.with_name(".review.md.review.tmp")
    state_temporary = context.state_path.with_name(".state.json.review.tmp")
    review_temporary_created = False
    state_temporary_created = False
    try:
        with review_temporary.open("x", encoding="utf-8") as stream:
            stream.write(report)
        review_temporary_created = True
        with state_temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(context.state, indent=2)}\n")
        state_temporary_created = True
        if (
            _read_text(context.state_path, "Session state") != context.raw_state
            or _read_text(context.review_path, "Review artifact") != context.raw_review
        ):
            raise ImplementationReviewError("Review inputs changed concurrently")
        review_temporary.replace(context.review_path)
        state_temporary.replace(context.state_path)
    except FileExistsError as error:
        raise ImplementationReviewError(
            "Review update is already in progress"
        ) from error
    except OSError as error:
        raise ImplementationReviewError(
            "Review artifacts could not be updated"
        ) from error
    finally:
        created_temporaries = (
            (review_temporary, review_temporary_created),
            (state_temporary, state_temporary_created),
        )
        for temporary, was_created in created_temporaries:
            if was_created and temporary.exists():
                temporary.unlink()


def run_active_implementation_review(root: Path) -> ImplementationReviewRun:
    """Run the deterministic audit-integrity review for the active Session."""
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise ImplementationReviewError("Project status could not be read") from error
    if status.current_session is None:
        raise ImplementationReviewError("Project has no active Session")
    context = _load_context(root, status.current_session)
    report = _render_report(context)
    _write_review(context, report)
    return ImplementationReviewRun(
        context.session_id,
        context.final_test_id,
        len(context.completed_tests),
        context.completion_sha256,
        hashlib.sha256(report.encode("utf-8")).hexdigest(),
    )
