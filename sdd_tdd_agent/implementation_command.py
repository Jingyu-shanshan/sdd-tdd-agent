from pathlib import Path
from typing import Optional, Union

from sdd_tdd_agent.execution_config import load_test_command_timeout
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.production_source_command import (
    ProductionSourceCommandRun,
    generate_active_production_source,
)
from sdd_tdd_agent.red_execution import (
    RedExecutionRun,
    TestCommandRunner,
    execute_current_test_for_red,
    has_test_source_artifact_record,
    is_current_test_source_recorded,
)
from sdd_tdd_agent.test_source_command import (
    TestSourceCommandRun,
    generate_active_test_source,
)
from sdd_tdd_agent.tdd_cycle import load_current_tdd_phase


ImplementationCommandRun = Union[
    TestSourceCommandRun,
    RedExecutionRun,
    ProductionSourceCommandRun,
]


def continue_active_implementation(
    root: Path,
    model_runner: ProcessRunner,
    test_runner: TestCommandRunner,
    command_resolver: Optional[CodexCommandResolver] = None,
) -> ImplementationCommandRun:
    """Perform exactly one next action for the active IMPLEMENTATION Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ValueError("Project has no active Session")
    session_id = status.current_session
    phase = load_current_tdd_phase(root, session_id)
    if phase in {None, "WRITE_TEST"}:
        if not is_current_test_source_recorded(root, session_id):
            return generate_active_test_source(
                root,
                model_runner,
                command_resolver=command_resolver,
            )
        timeout_seconds = load_test_command_timeout(root)
        return execute_current_test_for_red(
            root,
            session_id,
            test_runner,
            timeout_seconds,
        )
    if phase == "RED":
        if not has_test_source_artifact_record(root, session_id):
            raise ValueError("A TDD cycle is already active")
        return generate_active_production_source(
            root,
            model_runner,
            command_resolver=command_resolver,
        )
    raise ValueError(f"Current TDD cycle phase {phase} is not supported yet")
