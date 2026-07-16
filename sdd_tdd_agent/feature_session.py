from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sdd_tdd_agent.session_creation import create_session


@dataclass(frozen=True)
class FeatureSession:
    """A newly created feature session."""

    session_id: str
    path: Path


def create_feature_session(
    root: Path,
    description: str,
    session_id: Optional[str] = None,
) -> FeatureSession:
    """Create an exclusive feature session containing initial SDD artifacts."""
    session = create_session(root, description, "feature", session_id)
    return FeatureSession(session.session_id, session.path)
