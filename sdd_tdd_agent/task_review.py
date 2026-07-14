import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from sdd_tdd_agent.project_status import load_project_status


REVIEW_STATE = "TASK_REVIEW"
TASK_HEADING = "# Task Breakdown"


class TaskReviewError(ValueError):
    """Safe error raised for an invalid task review operation."""


@dataclass(frozen=True)
class TaskReview:
    """The active generated task breakdown at the human review gate."""

    session_id: str
    state: str
    tasks: str


@dataclass(frozen=True)
class TaskReviewDecision:
    """A completed human task decision and workflow transition."""

    session_id: str
    decision: str
    previous_state: str
    next_state: str
    reason: Optional[str]


@dataclass(frozen=True)
class _ReviewContext:
    session_id: str
    session_path: Path
    state: Dict[str, object]
    tasks: str


def _has_approval(state: Dict[str, object], key: str) -> bool:
    review = state.get(key)
    return isinstance(review, dict) and review.get("decision") == "approved"


def _load_active_context(root: Path) -> _ReviewContext:
    try:
        status = load_project_status(root)
    except (FileNotFoundError, KeyError) as error:
        raise TaskReviewError("Unable to load active Session") from error
    except json.JSONDecodeError as error:
        raise TaskReviewError("Session state is not valid JSON") from error
    except ValueError as error:
        raise TaskReviewError(str(error)) from error
    if status.current_session is None:
        raise TaskReviewError("Project has no active Session")

    session_id = status.current_session
    session_path = root / ".agent" / "sessions" / session_id
    state_path = session_path / "state.json"
    try:
        state_value = json.loads(state_path.read_text(encoding="utf-8"))
        tasks = (session_path / "tasks.md").read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise TaskReviewError("Active Session task review files are missing") from error
    except json.JSONDecodeError as error:
        raise TaskReviewError("Session state is not valid JSON") from error
    except UnicodeError as error:
        raise TaskReviewError(
            "Active Session task review files are not UTF-8"
        ) from error

    if not isinstance(state_value, dict):
        raise TaskReviewError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise TaskReviewError("Session state identifier does not match active Session")
    if state.get("state") != REVIEW_STATE:
        raise TaskReviewError("Task review requires TASK_REVIEW state")
    if not _has_approval(state, "requirement_review"):
        raise TaskReviewError("Task review requires approved requirements")
    if not _has_approval(state, "design_review"):
        raise TaskReviewError("Task review requires approved design")
    if not tasks.strip():
        raise TaskReviewError("Tasks must not be empty")
    if not tasks.lstrip().startswith(TASK_HEADING):
        raise TaskReviewError("Task review requires generated tasks")
    return _ReviewContext(session_id, session_path, state, tasks)


def load_active_task_review(root: Path) -> TaskReview:
    """Load the active generated tasks without changing Session state."""
    context = _load_active_context(root)
    return TaskReview(
        session_id=context.session_id,
        state=REVIEW_STATE,
        tasks=context.tasks,
    )


def _write_decision(
    context: _ReviewContext,
    decision: str,
    next_state: str,
    reason: Optional[str],
) -> TaskReviewDecision:
    review_record = {"decision": decision}
    if reason is not None:
        review_record["reason"] = reason
    context.state["state"] = next_state
    context.state["task_review"] = review_record
    serialized = f"{json.dumps(context.state, indent=2)}\n"
    state_path = context.session_path / "state.json"
    temporary = context.session_path / ".state.json.task-review.tmp"
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(state_path)
    except OSError as error:
        raise TaskReviewError("Unable to update Session state") from error
    return TaskReviewDecision(
        session_id=context.session_id,
        decision=decision,
        previous_state=REVIEW_STATE,
        next_state=next_state,
        reason=reason,
    )


def approve_active_tasks(root: Path) -> TaskReviewDecision:
    """Approve active generated tasks and enter TEST_GENERATION."""
    context = _load_active_context(root)
    return _write_decision(context, "approved", "TEST_GENERATION", None)


def reject_active_tasks(root: Path, reason: str) -> TaskReviewDecision:
    """Reject active generated tasks and return to TASK_BREAKDOWN."""
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise TaskReviewError("Task rejection reason must not be empty")
    context = _load_active_context(root)
    return _write_decision(
        context,
        "rejected",
        "TASK_BREAKDOWN",
        normalized_reason,
    )
