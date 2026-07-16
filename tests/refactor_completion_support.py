from pathlib import Path

from sdd_tdd_agent.implementation_review import run_active_implementation_review
from tests.implementation_review_support import create_review_workspace


def create_refactor_workspace(root: Path) -> Path:
    session = create_review_workspace(root)
    run_active_implementation_review(root)
    return session
