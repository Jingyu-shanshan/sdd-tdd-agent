from pathlib import Path
from typing import Optional

from sdd_tdd_agent.analyze_command import (
    ActiveSessionError,
    load_analyzer_config,
)
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.task_adapter import (
    CodexExecTaskBreakdownGenerator,
    JsonCommandTaskBreakdownGenerator,
)
from sdd_tdd_agent.task_breakdown import TaskBreakdownRun, run_task_breakdown


def generate_active_tasks(
    root: Path,
    runner: ProcessRunner,
    command_resolver: Optional[CodexCommandResolver] = None,
) -> TaskBreakdownRun:
    """Generate tasks for the configured active project Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_analyzer_config(root)
    if config.protocol == "codex-exec":
        generator = CodexExecTaskBreakdownGenerator(
            config=config,
            runner=runner,
            workspace=root,
            command_resolver=command_resolver,
        )
    else:
        generator = JsonCommandTaskBreakdownGenerator(
            config=config,
            runner=structured_cli_runner(config, runner),
        )
    return run_task_breakdown(root, status.current_session, generator)
