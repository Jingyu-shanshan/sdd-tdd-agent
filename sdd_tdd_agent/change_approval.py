import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Literal, Optional, Tuple, Union, cast

from sdd_tdd_agent.project_status import load_project_status


ChangeKind = Literal["added", "modified", "deleted"]
RiskLevel = Literal["low", "medium", "high"]
ApprovalDecision = Literal["pending", "approved", "rejected", "not_required"]
JsonValue = Union[None, bool, int, float, str, list[object], Dict[str, object]]

_CHANGE_KINDS = {"added", "modified", "deleted"}
_DECISIONS = {"pending", "approved", "rejected", "not_required"}
_RISK_LEVELS = {"low", "medium", "high"}
_CONTROL_PATHS = {".agent/config.yml", "AGENTS.md"}
_DEPENDENCY_FILES = {
    "angular.json",
    "build.gradle",
    "build.gradle.kts",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "settings.gradle",
    "settings.gradle.kts",
}
_REASON_RISK: Dict[str, RiskLevel] = {
    "documentation/test evidence only": "low",
    "production change": "medium",
    "deletion": "high",
    "project control change": "high",
    "dependency change": "high",
}
_RISK_RANK = {"low": 0, "medium": 1, "high": 2}
_MAX_RECORD_BYTES = 8_192
_MAX_REJECTION_REASON = 500


class ChangeApprovalError(ValueError):
    """Safe error raised for an invalid change-approval operation."""


@dataclass(frozen=True)
class ProjectChange:
    """One candidate project path and its Git change kind."""

    path: str
    kind: str


@dataclass(frozen=True)
class ChangeRisk:
    """Canonical risk assessment bound to an exact path/kind set."""

    changes: Tuple[ProjectChange, ...]
    change_digest: str
    level: RiskLevel
    reasons: Tuple[str, ...]
    requires_human_approval: bool


@dataclass(frozen=True)
class ChangeApproval:
    """One persisted decision for the active Session and change digest."""

    session_id: str
    operation: str
    change_digest: str
    risk_level: RiskLevel
    reasons: Tuple[str, ...]
    decision: ApprovalDecision
    reason: Optional[str]


def _validate_change(change: ProjectChange) -> ProjectChange:
    path = change.path
    pure_path = PurePosixPath(path)
    if (
        not path
        or len(path) > 500
        or "\\" in path
        or "\x00" in path
        or pure_path.is_absolute()
        or path != pure_path.as_posix()
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise ChangeApprovalError("Change must use a safe relative path")
    if change.kind not in _CHANGE_KINDS:
        raise ChangeApprovalError("Unsupported change kind")
    return ProjectChange(path, change.kind)


def _change_reason(change: ProjectChange) -> str:
    if change.kind == "deleted":
        return "deletion"
    if change.path in _CONTROL_PATHS or change.path.startswith(".github/"):
        return "project control change"
    if PurePosixPath(change.path).name in _DEPENDENCY_FILES:
        return "dependency change"
    if (
        change.path.endswith(".md")
        or change.path.startswith("docs/")
        or change.path.startswith("tests/")
        or change.path.startswith(".agent/sessions/")
    ):
        return "documentation/test evidence only"
    return "production change"


def _canonical_digest(changes: Tuple[ProjectChange, ...]) -> str:
    payload = [{"kind": change.kind, "path": change.path} for change in changes]
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assess_change_risk(changes: Tuple[ProjectChange, ...]) -> ChangeRisk:
    """Validate and deterministically classify one exact project change set."""
    if not changes:
        raise ChangeApprovalError("Change set must not be empty")
    validated = tuple(
        sorted((_validate_change(item) for item in changes), key=lambda x: x.path)
    )
    if len({item.path for item in validated}) != len(validated):
        raise ChangeApprovalError("Change paths must be unique")
    reasons = tuple(
        sorted(
            {_change_reason(item) for item in validated},
            key=lambda reason: (-_RISK_RANK[_REASON_RISK[reason]], reason),
        )
    )
    level = cast(
        RiskLevel,
        max(
            (_REASON_RISK[reason] for reason in reasons),
            key=lambda item: _RISK_RANK[item],
        ),
    )
    return ChangeRisk(
        changes=validated,
        change_digest=_canonical_digest(validated),
        level=level,
        reasons=reasons,
        requires_human_approval=level != "low",
    )


def _active_session(root: Path) -> Tuple[str, Path]:
    try:
        status = load_project_status(root)
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise ChangeApprovalError("Unable to load active Session") from error
    if status.current_session is None:
        raise ChangeApprovalError("Project has no active Session")
    if status.session_state != "DONE":
        raise ChangeApprovalError("Change approval requires DONE state")
    path = root / ".agent" / "sessions" / status.current_session
    if path.is_symlink() or not path.is_dir():
        raise ChangeApprovalError("Active Session path must be a regular directory")
    return status.current_session, path


def _reject_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> Dict[str, JsonValue]:
    result: Dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise ChangeApprovalError("Change approval record is invalid")
        result[key] = value
    return result


def _read_payload(path: Path) -> Dict[str, JsonValue]:
    if path.is_symlink() or not path.is_file():
        raise ChangeApprovalError("Change approval record must be a regular file")
    try:
        content = path.read_bytes()
        if len(content) > _MAX_RECORD_BYTES:
            raise ChangeApprovalError("Change approval record is invalid")
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ChangeApprovalError("Change approval record is invalid") from error
    if not isinstance(value, dict):
        raise ChangeApprovalError("Change approval record is invalid")
    return value


def _validated_reasons(value: object, risk_level: RiskLevel) -> Tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > len(_REASON_RISK):
        raise ChangeApprovalError("Change approval record is invalid")
    if any(not isinstance(item, str) or item not in _REASON_RISK for item in value):
        raise ChangeApprovalError("Change approval record is invalid")
    reasons = cast(Tuple[str, ...], tuple(value))
    if (
        tuple(
            sorted(
                set(reasons), key=lambda item: (-_RISK_RANK[_REASON_RISK[item]], item)
            )
        )
        != reasons
    ):
        raise ChangeApprovalError("Change approval record is invalid")
    derived = max(
        (_REASON_RISK[item] for item in reasons),
        key=lambda item: _RISK_RANK[item],
    )
    if derived != risk_level:
        raise ChangeApprovalError("Change approval record is invalid")
    return reasons


def _decode_approval(payload: Dict[str, JsonValue], session_id: str) -> ChangeApproval:
    decision = payload.get("decision")
    expected = {
        "schema_version",
        "session_id",
        "operation",
        "change_digest",
        "risk_level",
        "reasons",
        "decision",
    }
    if decision == "rejected":
        expected.add("reason")
    if set(payload) != expected or payload.get("schema_version") != 1:
        raise ChangeApprovalError("Change approval record is invalid")
    if payload.get("session_id") != session_id:
        raise ChangeApprovalError("Change approval does not match active Session")
    if payload.get("operation") != "git_commit" or decision not in _DECISIONS:
        raise ChangeApprovalError("Change approval record is invalid")
    digest = payload.get("change_digest")
    risk = payload.get("risk_level")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ChangeApprovalError("Change approval record is invalid")
    if not isinstance(risk, str) or risk not in _RISK_LEVELS:
        raise ChangeApprovalError("Change approval record is invalid")
    risk_level = cast(RiskLevel, risk)
    if (decision == "not_required") != (risk_level == "low"):
        raise ChangeApprovalError("Change approval record is invalid")
    reason = payload.get("reason")
    if decision == "rejected" and (
        not isinstance(reason, str) or not reason or len(reason) > _MAX_REJECTION_REASON
    ):
        raise ChangeApprovalError("Change approval record is invalid")
    return ChangeApproval(
        session_id,
        "git_commit",
        digest,
        risk_level,
        _validated_reasons(payload.get("reasons"), risk_level),
        cast(ApprovalDecision, decision),
        cast(Optional[str], reason),
    )


def _approval_payload(approval: ChangeApproval) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "schema_version": 1,
        "session_id": approval.session_id,
        "operation": approval.operation,
        "change_digest": approval.change_digest,
        "risk_level": approval.risk_level,
        "reasons": list(approval.reasons),
        "decision": approval.decision,
    }
    if approval.reason is not None:
        payload["reason"] = approval.reason
    return payload


def _atomic_write(
    path: Path, approval: ChangeApproval, original: Optional[bytes]
) -> None:
    temporary = path.with_name(".change-approval.json.tmp")
    serialized = f"{json.dumps(_approval_payload(approval), indent=2)}\n"
    try:
        with temporary.open("x", encoding="utf-8") as file:
            file.write(serialized)
    except FileExistsError as error:
        raise ChangeApprovalError(
            "Change approval update already in progress"
        ) from error
    try:
        current = path.read_bytes() if path.exists() else None
        if path.is_symlink() or current != original:
            raise ChangeApprovalError("Change approval changed concurrently")
        temporary.replace(path)
    except OSError as error:
        raise ChangeApprovalError("Unable to update change approval") from error
    finally:
        if temporary.exists():
            temporary.unlink()


def load_active_change_approval(root: Path) -> ChangeApproval:
    """Load and validate the active Session change-approval record."""
    session_id, session_path = _active_session(root)
    return _decode_approval(
        _read_payload(session_path / "change-approval.json"),
        session_id,
    )


def request_active_change_approval(root: Path, risk: ChangeRisk) -> ChangeApproval:
    """Create an exact idempotent approval request for the active Session."""
    if assess_change_risk(risk.changes) != risk:
        raise ChangeApprovalError("Change risk assessment is invalid")
    session_id, session_path = _active_session(root)
    path = session_path / "change-approval.json"
    decision: ApprovalDecision = (
        "pending" if risk.requires_human_approval else "not_required"
    )
    requested = ChangeApproval(
        session_id,
        "git_commit",
        risk.change_digest,
        risk.level,
        risk.reasons,
        decision,
        None,
    )
    if path.exists() or path.is_symlink():
        existing = _decode_approval(_read_payload(path), session_id)
        existing_identity = (
            existing.session_id,
            existing.operation,
            existing.change_digest,
            existing.risk_level,
            existing.reasons,
        )
        requested_identity = (
            requested.session_id,
            requested.operation,
            requested.change_digest,
            requested.risk_level,
            requested.reasons,
        )
        if existing_identity != requested_identity:
            raise ChangeApprovalError("Existing approval is for a different change set")
        return existing
    _atomic_write(path, requested, None)
    return requested


def _decide(
    root: Path, decision: ApprovalDecision, reason: Optional[str]
) -> ChangeApproval:
    session_id, session_path = _active_session(root)
    path = session_path / "change-approval.json"
    original = path.read_bytes() if path.exists() and not path.is_symlink() else None
    current = _decode_approval(_read_payload(path), session_id)
    if current.decision != "pending":
        raise ChangeApprovalError("Change approval is not pending")
    decided = ChangeApproval(
        current.session_id,
        current.operation,
        current.change_digest,
        current.risk_level,
        current.reasons,
        decision,
        reason,
    )
    _atomic_write(path, decided, original)
    return decided


def approve_active_change(root: Path) -> ChangeApproval:
    """Explicitly approve the active pending medium/high-risk change set."""
    return _decide(root, "approved", None)


def reject_active_change(root: Path, reason: str) -> ChangeApproval:
    """Explicitly reject the active pending change set with a bounded reason."""
    normalized = reason.strip()
    if not normalized:
        raise ChangeApprovalError("Rejection reason must not be empty")
    if len(normalized) > _MAX_REJECTION_REASON:
        raise ChangeApprovalError("Rejection reason is too long")
    return _decide(root, "rejected", normalized)


def render_change_approval(approval: ChangeApproval) -> str:
    """Render a deterministic source-free approval status."""
    reasons = ", ".join(approval.reasons)
    return (
        f"Change approval: {approval.decision}\n"
        f"Session: {approval.session_id}\n"
        f"Operation: {approval.operation}\n"
        f"Risk: {approval.risk_level}\n"
        f"Digest: {approval.change_digest}\n"
        f"Reasons: {reasons}\n"
    )
