from pathlib import Path
from typing import Optional

from sdd_tdd_agent.analyze_command import ActiveSessionError, load_analyzer_config
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.test_adapter import (
    CodexExecTestPlanGenerator,
    JsonCommandTestPlanGenerator,
)
from sdd_tdd_agent.test_generation import TestGenerationRun, run_test_generation


def generate_active_test_plan(
    root: Path,
    runner: ProcessRunner,
    command_resolver: Optional[CodexCommandResolver] = None,
) -> TestGenerationRun:
    """Generate a test plan for the configured active project Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_analyzer_config(root)
    if config.protocol == "codex-exec":
        generator = CodexExecTestPlanGenerator(
            config=config,
            runner=runner,
            workspace=root,
            command_resolver=command_resolver,
        )
    else:
        generator = JsonCommandTestPlanGenerator(
            config=config,
            runner=structured_cli_runner(config, runner),
        )
    return run_test_generation(root, status.current_session, generator)
