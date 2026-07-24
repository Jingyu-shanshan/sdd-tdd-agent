import io
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from sdd_tdd_agent.chat_adapter import ConversationReply, ConversationRequest
from sdd_tdd_agent.interactive_shell import (
    CommandResult,
    InteractiveLaunch,
    MenuOption,
    PromptToolkitInteractiveShell,
)
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies


class FakeTerminal:
    def __init__(
        self,
        choices: Sequence[str],
        inputs: Sequence[Optional[str]],
    ) -> None:
        self.choices = list(choices)
        self.inputs = list(inputs)
        self.output: List[str] = []
        self.menus: List[Tuple[str, Tuple[MenuOption, ...]]] = []

    def write(self, value: str) -> None:
        self.output.append(value)

    def choose(
        self,
        title: str,
        options: Tuple[MenuOption, ...],
    ) -> Optional[str]:
        self.menus.append((title, options))
        return self.choices.pop(0) if self.choices else None

    def prompt(self, message: str) -> Optional[str]:
        return self.inputs.pop(0)


class UnexpectedRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Non-TTY provider selection must not run a process")


class UnexpectedLocator:
    def locate(self, executable: str) -> Optional[str]:
        raise AssertionError("Non-TTY provider selection must not locate a CLI")


class UnexpectedAgent:
    def respond(self, request: ConversationRequest) -> ConversationReply:
        raise AssertionError("No Provider chat was requested")


def test_should_initialize_and_select_both_provider_roles(tmp_path: Path) -> None:
    terminal = FakeTerminal(["claude-code", "pi"], ["/exit"])
    commands: List[Tuple[str, ...]] = []
    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=lambda arguments: _record(commands, arguments),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    exit_code = shell.run(tmp_path, InteractiveLaunch("new"))

    assert exit_code == 0
    config = (tmp_path / ".agent" / "config.yml").read_text(encoding="utf-8")
    assert "production_source_provider: claude-code" in config
    assert "test_source_provider: pi" in config
    assert [title for title, _ in terminal.menus] == [
        "Select the code Provider",
        "Select the test Provider",
    ]
    assert any("🐳" in value for value in terminal.output)
    assert commands == []


def test_should_execute_typed_chat_action_through_command_boundary(
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal(["codex", "codex"], ["/exit"])
    commands: List[Tuple[str, ...]] = []

    class StatusAgent:
        def respond(self, request: ConversationRequest) -> ConversationReply:
            assert request.user_message == "Where are we?"
            return ConversationReply("Checking.", "show_status", None)

    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=StatusAgent(),
        command_executor=lambda arguments: _record(commands, arguments),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    exit_code = shell.run(
        tmp_path,
        InteractiveLaunch("new", initial_prompt="Where are we?"),
    )

    assert exit_code == 0
    assert commands == [("status",)]
    session_path = next((tmp_path / ".agent" / "logs" / "chat").glob("*.jsonl"))
    content = session_path.read_text(encoding="utf-8")
    assert "Where are we?" in content
    assert "Checking." in content
    assert "Workflow command completed (status; exit 0)." in content
    assert "Project: demo" not in content


def _record(
    commands: List[Tuple[str, ...]],
    arguments: Sequence[str],
) -> CommandResult:
    command = tuple(arguments)
    commands.append(command)
    if command == ("status",):
        return CommandResult(0, "Project: demo\nState: none\n", "")
    return CommandResult(0, "ok\n", "")
