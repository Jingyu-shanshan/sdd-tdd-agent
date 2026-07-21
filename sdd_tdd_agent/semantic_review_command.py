from pathlib import Path
from typing import Optional

from sdd_tdd_agent.analyze_command import ActiveSessionError, load_analyzer_config
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.semantic_review import SemanticReviewRun, run_semantic_review
from sdd_tdd_agent.semantic_review_adapter import (
    CodexExecSemanticReviewer,
    JsonCommandSemanticReviewer,
)


def run_active_semantic_review(
    root: Path,
    runner: ProcessRunner,
    command_resolver: Optional[CodexCommandResolver] = None,
) -> SemanticReviewRun:
    """Run semantic review for the active completed implementation."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_analyzer_config(root)
    if config.protocol == "codex-exec":
        reviewer = CodexExecSemanticReviewer(
            config,
            runner,
            root,
            command_resolver=command_resolver,
        )
    else:
        reviewer = JsonCommandSemanticReviewer(
            config,
            structured_cli_runner(config, runner),
        )
    return run_semantic_review(root, status.current_session, reviewer)
