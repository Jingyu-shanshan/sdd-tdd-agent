import io
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from sdd_tdd_agent.chat_adapter import ConversationReply, ConversationRequest
from sdd_tdd_agent.chat_session import ChatSessionStore
from sdd_tdd_agent.interactive_shell import (
    CommandResult,
    INTERRUPT_SENTINEL,
    InteractiveLaunch,
    MenuOption,
    PromptToolkitInteractiveShell,
    _captures_code_diff,
)
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.terminal_theme import InteractiveTheme
from sdd_tdd_agent.workspace_diff import WorkspaceDiffSnapshot


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


class RecordingClipboard:
    def __init__(self) -> None:
        self.values: List[str] = []

    def copy(self, value: str) -> None:
        self.values.append(value)


class FixedDiffCollector:
    def snapshot(self) -> WorkspaceDiffSnapshot:
        return WorkspaceDiffSnapshot(
            (
                (
                    "app.py",
                    "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
                ),
            )
        )


class ChangingDiffCollector:
    def __init__(self) -> None:
        self.calls = 0

    def snapshot(self) -> WorkspaceDiffSnapshot:
        self.calls += 1
        if self.calls == 1:
            return WorkspaceDiffSnapshot(())
        return FixedDiffCollector().snapshot()


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
    banner = "".join(terminal.output)
    assert "🐳" not in banner
    assert "████" in banner
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


def test_should_load_selected_skill_and_copy_latest_reply(tmp_path: Path) -> None:
    skill = tmp_path / ".agents" / "skills" / "review" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: review\ndescription: Review code.\n---\n\nPROJECT SKILL\n",
        encoding="utf-8",
    )
    terminal = FakeTerminal(
        ["codex", "codex", "review"],
        ["/skills", "Review this", "/copy", "/exit"],
    )
    clipboard = RecordingClipboard()

    class SkillAgent:
        def respond(self, request: ConversationRequest) -> ConversationReply:
            assert request.skill is not None
            assert request.skill.name == "review"
            assert "PROJECT SKILL" in request.skill.content
            return ConversationReply("Reviewed.", None, None)

    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=SkillAgent(),
        command_executor=lambda arguments: CommandResult(0, "", ""),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
        clipboard=clipboard,
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0
    assert clipboard.values == ["Reviewed."]


def test_should_send_attachment_without_persisting_file_content(
    tmp_path: Path,
) -> None:
    (tmp_path / "app.py").write_text(
        "ATTACHMENT-CONTENT-SENTINEL\n",
        encoding="utf-8",
    )
    terminal = FakeTerminal(
        ["codex", "codex"],
        ["Review @app.py", "/exit"],
    )

    class AttachmentAgent:
        def respond(self, request: ConversationRequest) -> ConversationReply:
            assert request.attachments[0].path == "app.py"
            assert "ATTACHMENT-CONTENT-SENTINEL" in request.attachments[0].content
            return ConversationReply("Reviewed attachment.", None, None)

    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=AttachmentAgent(),
        command_executor=lambda arguments: CommandResult(0, "", ""),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0
    session_path = next((tmp_path / ".agent" / "logs" / "chat").glob("*.jsonl"))
    content = session_path.read_text(encoding="utf-8")
    assert "Attachments sent: app.py" in content
    assert "ATTACHMENT-CONTENT-SENTINEL" not in content


def test_should_cancel_current_command_without_exiting_chat(tmp_path: Path) -> None:
    terminal = FakeTerminal(
        ["codex", "codex"],
        ["/status", "/exit"],
    )

    def cancel(arguments: Sequence[str]) -> CommandResult:
        raise KeyboardInterrupt

    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=cancel,
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0
    assert "Execution cancelled.\n" in terminal.output


def test_should_render_current_diff_with_terminal_theme(tmp_path: Path) -> None:
    terminal = FakeTerminal(
        ["codex", "codex"],
        ["/diff", "/exit"],
    )
    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=lambda arguments: CommandResult(0, "", ""),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
        theme=InteractiveTheme(enabled=True),
        diff_collector=FixedDiffCollector(),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0

    output = "".join(terminal.output)
    assert "\x1b[38;5;203m-old" in output
    assert "\x1b[38;5;114m+new" in output


def test_should_capture_diff_only_for_source_writing_commands() -> None:
    assert _captures_code_diff(("continue",))
    assert _captures_code_diff(("refactor", "automated"))
    assert not _captures_code_diff(("status",))
    assert not _captures_code_diff(("refactor",))


def test_should_support_pi_command_aliases_and_double_ctrl_c(
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal(
        ["codex", "codex"],
        ["/name focused", "/hotkeys", INTERRUPT_SENTINEL, INTERRUPT_SENTINEL],
    )
    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=lambda arguments: CommandResult(0, "", ""),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0

    output = "".join(terminal.output)
    assert "Chat renamed: focused" in output
    assert "Ctrl+C" in output
    assert "Press Ctrl+C again to exit." in output


def test_should_show_shortcuts_for_question_mark_without_calling_agent(
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal(
        ["codex", "codex"],
        ["?", "/exit"],
    )
    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=lambda arguments: CommandResult(0, "", ""),
        provider_dependencies=ProviderCommandDependencies(
            io.StringIO(),
            UnexpectedRunner(),
            UnexpectedLocator(),
        ),
    )

    assert shell.run(tmp_path, InteractiveLaunch("new")) == 0
    assert "@                        Open project file search" in "".join(
        terminal.output
    )


def test_should_show_new_diff_after_source_writing_command(
    tmp_path: Path,
) -> None:
    terminal = FakeTerminal([], [])
    collector = ChangingDiffCollector()
    shell = PromptToolkitInteractiveShell(
        terminal=terminal,
        agent=UnexpectedAgent(),
        command_executor=lambda arguments: CommandResult(
            0,
            "Test source ready for RED.\n",
            "",
        ),
        theme=InteractiveTheme(enabled=True),
        diff_collector=collector,
    )
    initialize_project(tmp_path)
    store = ChatSessionStore(tmp_path)
    session = store.create()

    assert shell._execute(tmp_path, store, session, ("continue",))

    output = "".join(terminal.output)
    assert "Code changes" in output
    assert "\x1b[38;5;203m-old" in output
    assert "\x1b[38;5;114m+new" in output


def _record(
    commands: List[Tuple[str, ...]],
    arguments: Sequence[str],
) -> CommandResult:
    command = tuple(arguments)
    commands.append(command)
    if command == ("status",):
        return CommandResult(0, "Project: demo\nState: none\n", "")
    return CommandResult(0, "ok\n", "")
