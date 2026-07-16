from pathlib import Path

from sdd_tdd_agent.cycle_completion import complete_active_implementation
from tests.cycle_completion_support import create_green_workspace


PENDING_REVIEW = "# Review\n\nPending requirement analysis.\n"


def create_review_workspace(root: Path) -> Path:
    session = create_green_workspace(root)
    (session / "review.md").write_text(PENDING_REVIEW, encoding="utf-8")
    complete_active_implementation(root)
    return session
