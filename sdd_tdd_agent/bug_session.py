from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sdd_tdd_agent.session_creation import create_session


@dataclass(frozen=True)
class BugSession:
    """A newly created bug Session."""

    session_id: str
    path: Path


def create_bug_session(
    root: Path,
    description: str,
    session_id: Optional[str] = None,
) -> BugSession:
    """Create an exclusive bug Session containing initial SDD artifacts."""
    session = create_session(root, description, "bug", session_id)
    return BugSession(session.session_id, session.path)
