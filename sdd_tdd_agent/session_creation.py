import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional


SessionKind = Literal["feature", "bug"]


@dataclass(frozen=True)
class CreatedSession:
    """Internal result of creating and activating one development Session."""

    session_id: str
    path: Path


def _validate_session_id(session_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError(f"Invalid session identifier: {session_id}")


def _pending(title: str) -> str:
    return f"# {title}\n\nPending requirement analysis.\n"


def _generate_session_id(description: str, kind: SessionKind) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", description).strip("-").lower()
    safe_slug = slug[:40] or kind
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{safe_slug}"


def _activate_session(project_metadata: Path, session_id: str) -> None:
    original = project_metadata.read_text(encoding="utf-8")
    replacement = f"current_session: {session_id}\n"
    updated_lines = []
    is_replaced = False
    for line in original.splitlines(keepends=True):
        if line.startswith("current_session:"):
            updated_lines.append(replacement)
            is_replaced = True
        else:
            updated_lines.append(line)
    updated = "".join(updated_lines)
    if not is_replaced:
        if updated and not updated.endswith("\n"):
            updated += "\n"
        updated += replacement
    temporary = project_metadata.with_name(f".{project_metadata.name}.{session_id}.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(project_metadata)


def _artifacts(description: str, session_id: str, kind: SessionKind) -> dict[str, str]:
    state = {
        "session_id": session_id,
        "kind": kind,
        "state": "ANALYSIS",
        "current_task": None,
        "current_cycle": 0,
    }
    return {
        "requirement.md": f"# Requirement\n\n## User request\n\n{description}\n",
        "design.md": _pending("Design"),
        "tasks.md": _pending("Tasks"),
        "acceptance.md": _pending("Acceptance criteria"),
        "test-plan.md": _pending("Test plan"),
        "implementation.md": _pending("Implementation log"),
        "review.md": _pending("Review"),
        "state.json": f"{json.dumps(state, indent=2)}\n",
    }


def create_session(
    root: Path,
    description: str,
    kind: SessionKind,
    session_id: Optional[str] = None,
) -> CreatedSession:
    """Create and activate one exclusive feature or bug Session."""
    normalized_description = description.strip()
    if not normalized_description:
        raise ValueError(f"{kind.capitalize()} description must not be empty")
    resolved_id = session_id or _generate_session_id(normalized_description, kind)
    _validate_session_id(resolved_id)
    session_path = root / ".agent" / "sessions" / resolved_id
    session_path.mkdir(exist_ok=False)
    for filename, content in _artifacts(
        normalized_description,
        resolved_id,
        kind,
    ).items():
        (session_path / filename).write_text(content, encoding="utf-8")
    _activate_session(root / ".agent" / "project.yml", resolved_id)
    return CreatedSession(resolved_id, session_path)
