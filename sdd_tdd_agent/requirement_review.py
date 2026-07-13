import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from sdd_tdd_agent.project_status import load_project_status


REVIEW_STATE = "REQUIREMENT_REVIEW"


class RequirementReviewError(ValueError):
    """Safe error raised for an invalid requirement review operation."""


@dataclass(frozen=True)
class RequirementReview:
    """The active requirement presented at the human review gate."""

    session_id: str
    state: str
    requirement: str


@dataclass(frozen=True)
class RequirementReviewDecision:
    """A completed human decision and its workflow transition."""

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
    requirement: str


def _load_active_context(root: Path) -> _ReviewContext:
    try:
        status = load_project_status(root)
    except (FileNotFoundError, KeyError) as error:
        raise RequirementReviewError("Unable to load active Session") from error
    except json.JSONDecodeError as error:
        raise RequirementReviewError("Session state is not valid JSON") from error
    except ValueError as error:
        raise RequirementReviewError(str(error)) from error
    if status.current_session is None:
        raise RequirementReviewError("Project has no active Session")

    session_id = status.current_session
    session_path = root / ".agent" / "sessions" / session_id
    state_path = session_path / "state.json"
    try:
        state_value = json.loads(state_path.read_text(encoding="utf-8"))
        requirement = (session_path / "requirement.md").read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise RequirementReviewError(
            "Active Session review files are missing"
        ) from error
    except json.JSONDecodeError as error:
        raise RequirementReviewError("Session state is not valid JSON") from error
    except UnicodeError as error:
        raise RequirementReviewError(
            "Active Session review files are not UTF-8"
        ) from error

    if not isinstance(state_value, dict):
        raise RequirementReviewError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise RequirementReviewError(
            "Session state identifier does not match active Session"
        )
    if state.get("state") != REVIEW_STATE:
        raise RequirementReviewError(
            "Requirement review requires REQUIREMENT_REVIEW state"
        )
    if not requirement.strip():
        raise RequirementReviewError("Requirement must not be empty")
    return _ReviewContext(session_id, session_path, state, requirement)


def load_active_requirement_review(root: Path) -> RequirementReview:
    """Load the active analyzed requirement without changing Session state."""
    context = _load_active_context(root)
    return RequirementReview(
        session_id=context.session_id,
        state=REVIEW_STATE,
        requirement=context.requirement,
    )


def _write_decision(
    context: _ReviewContext,
    decision: str,
    next_state: str,
    reason: Optional[str],
) -> RequirementReviewDecision:
    review_record = {"decision": decision}
    if reason is not None:
        review_record["reason"] = reason
    context.state["state"] = next_state
    context.state["requirement_review"] = review_record
    serialized = f"{json.dumps(context.state, indent=2)}\n"
    state_path = context.session_path / "state.json"
    temporary = context.session_path / ".state.json.requirement-review.tmp"
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(state_path)
    except OSError as error:
        raise RequirementReviewError("Unable to update Session state") from error
    return RequirementReviewDecision(
        session_id=context.session_id,
        decision=decision,
        previous_state=REVIEW_STATE,
        next_state=next_state,
        reason=reason,
    )


def approve_active_requirement(root: Path) -> RequirementReviewDecision:
    """Approve the active analyzed requirement and enter DESIGN."""
    context = _load_active_context(root)
    return _write_decision(context, "approved", "DESIGN", None)


def reject_active_requirement(
    root: Path,
    reason: str,
) -> RequirementReviewDecision:
    """Reject the active analyzed requirement and return to ANALYSIS."""
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise RequirementReviewError("Rejection reason must not be empty")
    context = _load_active_context(root)
    return _write_decision(context, "rejected", "ANALYSIS", normalized_reason)
