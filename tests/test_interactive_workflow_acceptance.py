import io
import json
from pathlib import Path
from typing import Sequence, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.interactive_shell import (
    CommandResult,
    InteractiveLaunch,
    PromptToolkitInteractiveShell,
    _execution_provider_config,
)
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies
from tests.test_full_workflow_acceptance import (
    MODEL_RESPONSES,
    REQUIREMENT_SENTINEL,
    WorkflowTestRunner,
    _create_project,
)
from tests.test_interactive_shell import (
    FakeTerminal,
    UnexpectedAgent,
    UnexpectedLocator,
    UnexpectedRunner,
)


SEMANTIC_REVIEW = {
    "summary": "The completed implementation is safe.",
    "findings": [],
    "decision": "approved",
}


class InteractiveModelRunner:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        self.commands: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        del timeout_seconds
        request = json.loads(stdin)
        assert isinstance(request, dict)
        index = len(self.requests)
        response = MODEL_RESPONSES[index] if index < 6 else SEMANTIC_REVIEW
        self.requests.append(request)
        self.commands.append(command)
        if "--output-last-message" in command:
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps(response), encoding="utf-8")
            return ProcessResult(0, "progress", "")
        return ProcessResult(0, json.dumps(response), "")


def _prepare_project(root: Path) -> None:
    _create_project(root)
    initialize_project(root)
    config_path = root / ".agent" / "config.yml"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace(
        "test_command_timeout_seconds: 300",
        "test_command_timeout_seconds: 15",
    ).replace(
        "full_test_suite_timeout_seconds: 900",
        "full_test_suite_timeout_seconds: 60",
    )
    config_path.write_text(
        config
        + "requirement_analyzer_protocol: json-command\n"
        + "requirement_analyzer_command:\n"
        + '  - "model-bridge"\n'
        + "requirement_analyzer_timeout_seconds: 30\n",
        encoding="utf-8",
    )


def test_should_complete_dialog_sdd_tdd_review_and_verification(
    tmp_path: Path,
) -> None:
    _prepare_project(tmp_path)
    model_runner = InteractiveModelRunner()
    test_runner = WorkflowTestRunner()
    terminal = FakeTerminal(
        ["codex", "verify"],
        [
            f"/feature {REQUIREMENT_SENTINEL} export reports",
            "/approve",
            "/approve",
            "/approve",
            "/exit",
        ],
    )
    execution_protocols: list[str] = []

    def execute(arguments: Sequence[str]) -> CommandResult:
        if tuple(arguments) == ("continue",):
            execution_protocols.append(
                _execution_provider_config(tmp_path, arguments).protocol
            )
        output = io.StringIO()
        errors = io.StringIO()
        exit_code = main(
            arguments,
            out=output,
            err=errors,
            root=tmp_path,
            runner=model_runner,
            test_runner=test_runner,
        )
        return CommandResult(exit_code, output.getvalue(), errors.getvalue())

    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=execute,
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0

    status = load_project_status(tmp_path)
    assert status.session_state == "DONE", terminal.output
    assert status.current_session is not None
    state = json.loads(
        (
            tmp_path / ".agent" / "sessions" / status.current_session / "state.json"
        ).read_text(encoding="utf-8")
    )
    assert state["refactor"] == {
        "mode": "no_source_change",
        "decision": "verified",
    }
    transcript = "".join(terminal.output)
    assert transcript.index("RED confirmed") < transcript.index("GREEN confirmed")
    assert "Semantic review ready" in transcript
    assert "Implementation review passed" in transcript
    assert execution_protocols[0] == "codex-exec"
    assert "json-command" in execution_protocols
