import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from sdd_tdd_agent.project_status import load_project_status


REVIEW_STATE = "DESIGN_REVIEW"
DESIGN_HEADING = "# Design Proposal"


class DesignReviewError(ValueError):
    """Safe error raised for an invalid design review operation."""


@dataclass(frozen=True)
class DesignReview:
    """The active generated design presented at the human review gate."""

    session_id: str
    state: str
    design: str


@dataclass(frozen=True)
class DesignReviewDecision:
    """A completed human design decision and workflow transition."""

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
    design: str


def _load_active_context(root: Path) -> _ReviewContext:
    try:
        status = load_project_status(root)
    except (FileNotFoundError, KeyError) as error:
        raise DesignReviewError("Unable to load active Session") from error
    except json.JSONDecodeError as error:
        raise DesignReviewError("Session state is not valid JSON") from error
    except ValueError as error:
        raise DesignReviewError(str(error)) from error
    if status.current_session is None:
        raise DesignReviewError("Project has no active Session")

    session_id = status.current_session
    session_path = root / ".agent" / "sessions" / session_id
    state_path = session_path / "state.json"
    try:
        state_value = json.loads(state_path.read_text(encoding="utf-8"))
        design = (session_path / "design.md").read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise DesignReviewError(
            "Active Session design review files are missing"
        ) from error
    except json.JSONDecodeError as error:
        raise DesignReviewError("Session state is not valid JSON") from error
    except UnicodeError as error:
        raise DesignReviewError(
            "Active Session design review files are not UTF-8"
        ) from error

    if not isinstance(state_value, dict):
        raise DesignReviewError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise DesignReviewError(
            "Session state identifier does not match active Session"
        )
    if state.get("state") != REVIEW_STATE:
        raise DesignReviewError("Design review requires DESIGN_REVIEW state")
    requirement_review = state.get("requirement_review")
    if (
        not isinstance(requirement_review, dict)
        or requirement_review.get("decision") != "approved"
    ):
        raise DesignReviewError("Design review requires approved requirements")
    if not design.strip():
        raise DesignReviewError("Design must not be empty")
    if not design.lstrip().startswith(DESIGN_HEADING):
        raise DesignReviewError("Design review requires a generated design")
    return _ReviewContext(session_id, session_path, state, design)


def load_active_design_review(root: Path) -> DesignReview:
    """Load the active generated design without changing Session state."""
    context = _load_active_context(root)
    return DesignReview(
        session_id=context.session_id,
        state=REVIEW_STATE,
        design=context.design,
    )


def _write_decision(
    context: _ReviewContext,
    decision: str,
    next_state: str,
    reason: Optional[str],
) -> DesignReviewDecision:
    review_record = {"decision": decision}
    if reason is not None:
        review_record["reason"] = reason
    context.state["state"] = next_state
    context.state["design_review"] = review_record
    serialized = f"{json.dumps(context.state, indent=2)}\n"
    state_path = context.session_path / "state.json"
    temporary = context.session_path / ".state.json.design-review.tmp"
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(state_path)
    except OSError as error:
        raise DesignReviewError("Unable to update Session state") from error
    return DesignReviewDecision(
        session_id=context.session_id,
        decision=decision,
        previous_state=REVIEW_STATE,
        next_state=next_state,
        reason=reason,
    )


def approve_active_design(root: Path) -> DesignReviewDecision:
    """Approve the active generated design and enter TASK_BREAKDOWN."""
    context = _load_active_context(root)
    return _write_decision(context, "approved", "TASK_BREAKDOWN", None)


def reject_active_design(root: Path, reason: str) -> DesignReviewDecision:
    """Reject the active generated design and return to DESIGN."""
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise DesignReviewError("Design rejection reason must not be empty")
    context = _load_active_context(root)
    return _write_decision(context, "rejected", "DESIGN", normalized_reason)
