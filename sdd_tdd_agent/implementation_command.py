from pathlib import Path
from typing import Optional, Union

from sdd_tdd_agent.execution_config import load_test_command_timeout
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    ProcessRunner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    RedExecutionRun,
    TestCommandRunner,
    execute_current_test_for_red,
    is_current_test_source_recorded,
)
from sdd_tdd_agent.test_source_command import (
    TestSourceCommandRun,
    generate_active_test_source,
)


ImplementationCommandRun = Union[TestSourceCommandRun, RedExecutionRun]


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
