from pathlib import Path
from typing import Optional

from sdd_tdd_agent.analyze_command import ActiveSessionError
from sdd_tdd_agent.design_adapter import (
    CodexExecDesignGenerator,
    JsonCommandDesignGenerator,
)
from sdd_tdd_agent.design_generation import (
    DesignGenerationRun,
    run_design_generation,
)
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.provider_registry import load_primary_provider_config


def generate_active_design(
    root: Path,
    runner: ProcessRunner,
    command_resolver: Optional[CodexCommandResolver] = None,
) -> DesignGenerationRun:
    """Generate a design for the configured active project Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_primary_provider_config(root)
    if config.protocol == "codex-exec":
        generator = CodexExecDesignGenerator(
            config=config,
            runner=runner,
            workspace=root,
            command_resolver=command_resolver,
        )
    else:
        generator = JsonCommandDesignGenerator(
            config=config,
            runner=structured_cli_runner(config, runner),
        )
    return run_design_generation(root, status.current_session, generator)
