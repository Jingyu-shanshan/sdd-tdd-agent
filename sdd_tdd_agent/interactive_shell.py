import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional, Protocol, Sequence, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import Input
from prompt_toolkit.output import Output
from prompt_toolkit.shortcuts import CompleteStyle, radiolist_dialog
from prompt_toolkit.styles import Style

from sdd_tdd_agent.chat_adapter import (
    CodexExecConversationAgent,
    ConversationAgent,
    ConversationRequest,
    ConversationReply,
    JsonCommandConversationAgent,
)
from sdd_tdd_agent.chat_session import ChatSession, ChatSessionStore
from sdd_tdd_agent.clipboard import Clipboard, SystemClipboard
from sdd_tdd_agent.composer import PasteStore, WorkspaceCompleter, composer_bindings
from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessRunner,
    RequirementAnalyzerError,
    SubprocessRunner,
    SystemCodexCommandResolver,
    structured_cli_runner,
)
from sdd_tdd_agent.provider_streaming import (
    ProviderEvent,
    ProviderStreamingRunner,
    render_provider_event,
)
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.provider_registry import (
    ProviderDefinition,
    list_providers,
    load_primary_provider_config,
    load_provider_config,
    load_provider_roles_status,
)
from sdd_tdd_agent.provider_tools import (
    ProviderCommandDependencies,
    ProviderInstallError,
    use_provider,
)
from sdd_tdd_agent.red_execution import sanitize_public_text
from sdd_tdd_agent.skill_catalog import LoadedSkill, SkillCatalog
from sdd_tdd_agent.streaming_process import SystemStreamingProcessRunner
from sdd_tdd_agent.tdd_cycle import load_current_tdd_phase
from sdd_tdd_agent.terminal_theme import InteractiveTheme
from sdd_tdd_agent.workspace_attachments import WorkspaceAttachments
from sdd_tdd_agent.workspace_diff import (
    GitWorkspaceDiff,
    WorkspaceDiffCollector,
    WorkspaceDiffSnapshot,
)


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "conversation" / f"{PROMPT_VERSION}.md"
)
WHALE_LOGO = """\
          ▄████▄
     ▄████████████▄
  ▄██████████████████▄
 ███████████████▀  ▀███
  ▀██████████████████▀
     ▀▀████████▀▀
"""
REVIEW_STATES = {"REQUIREMENT_REVIEW", "DESIGN_REVIEW", "TASK_REVIEW"}
INTERRUPT_SENTINEL = "\0wssagent-interrupt\0"
PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "#00d7ff bold",
        "completion-menu": "bg:#20242e #d4d4d4",
        "completion-menu.completion": "bg:#20242e #d4d4d4",
        "completion-menu.completion.current": "bg:#3a3a4a #00d7ff bold",
        "completion-menu.meta.completion": "bg:#20242e #808080",
        "completion-menu.meta.completion.current": "bg:#3a3a4a #b5bd68",
        "bottom-toolbar": "bg:#1e1e24 #808080",
        "scrollbar.background": "bg:#20242e",
        "scrollbar.button": "bg:#505060",
    }
)


@dataclass(frozen=True)
class InteractiveLaunch:
    """Requested way to enter the interactive shell."""

    mode: Literal["new", "latest", "resume"]
    session_ref: Optional[str] = None
    initial_prompt: Optional[str] = None


class InteractiveShell(Protocol):
    """Typed boundary for the interactive terminal."""

    def run(self, root: Path, launch: InteractiveLaunch) -> int:
        """Run one interactive terminal session."""
        ...


@dataclass(frozen=True)
class MenuOption:
    """One visible interactive menu item."""

    value: str
    label: str
    enabled: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class CommandResult:
    """Captured result from the existing non-interactive CLI."""

    exit_code: int
    stdout: str
    stderr: str


class Terminal(Protocol):
    """Injectable terminal interaction boundary."""

    def write(self, value: str) -> None:
        """Write visible terminal content."""
        ...

    def choose(
        self,
        title: str,
        options: Tuple[MenuOption, ...],
    ) -> Optional[str]:
        """Choose one enabled value or cancel."""
        ...

    def prompt(self, message: str) -> Optional[str]:
        """Read one composer submission or return None at EOF."""
        ...


class PromptToolkitTerminal:
    """Production terminal built on prompt_toolkit and normal scrollback."""

    def __init__(
        self,
        input: Optional[Input] = None,
        output: Optional[Output] = None,
    ) -> None:
        self._root: Optional[Path] = None
        self._completer: Optional[WorkspaceCompleter] = None
        self._pastes = PasteStore()
        self._footer = ""
        self._color_enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        self._session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            key_bindings=composer_bindings(self._pastes),
            input=input,
            output=output,
            style=PROMPT_STYLE if self._color_enabled else None,
        )

    def configure(self, root: Path) -> None:
        """Bind completion and sanitization to one explicit project root."""
        self._root = root.resolve()
        self._completer = WorkspaceCompleter(root)

    def write(self, value: str) -> None:
        """Write to the ordinary terminal scroll region."""
        sys.stdout.write(value)
        sys.stdout.flush()

    def supports_color(self) -> bool:
        """Return whether this terminal should receive ANSI colors."""
        return self._color_enabled

    def set_footer(self, value: str) -> None:
        """Set compact context shown below the composer."""
        self._footer = value

    def choose(
        self,
        title: str,
        options: Tuple[MenuOption, ...],
    ) -> Optional[str]:
        """Display all options and allow arrows plus Enter for enabled ones."""
        disabled = [
            f"{option.label}: {option.reason}"
            for option in options
            if not option.enabled
        ]
        explanation = "\n".join(disabled) or "Use arrows and Enter."
        enabled = [(option.value, option.label) for option in options if option.enabled]
        if not enabled:
            self.write(f"{title}\n{explanation}\n")
            return None
        return radiolist_dialog(
            title=title,
            text=explanation,
            values=enabled,
        ).run()

    def prompt(self, message: str) -> Optional[str]:
        """Read one editable line while preserving terminal scrollback."""
        try:
            value = self._session.prompt(
                [("class:prompt", message.replace(" > ", " ❯ "))],
                completer=self._completer,
                complete_while_typing=True,
                complete_in_thread=True,
                complete_style=CompleteStyle.COLUMN,
                enable_history_search=False,
                reserve_space_for_menu=10,
                bottom_toolbar=self._footer or None,
            )
            expanded = self._pastes.expand(value)
            return (
                sanitize_public_text(self._root, expanded)
                if self._root is not None
                else expanded
            )
        except EOFError:
            return None
        except KeyboardInterrupt:
            self._pastes.expand("")
            self.write("^C\n")
            return INTERRUPT_SENTINEL


class PromptToolkitInteractiveShell:
    """Interactive facade over the existing validated SDD/TDD commands."""

    def __init__(
        self,
        terminal: Optional[Terminal] = None,
        agent: Optional[ConversationAgent] = None,
        command_executor: Optional[Callable[[Sequence[str]], CommandResult]] = None,
        provider_dependencies: Optional[ProviderCommandDependencies] = None,
        clipboard: Optional[Clipboard] = None,
        theme: Optional[InteractiveTheme] = None,
        diff_collector: Optional[WorkspaceDiffCollector] = None,
    ) -> None:
        self._terminal = terminal or PromptToolkitTerminal()
        supports_color = getattr(self._terminal, "supports_color", None)
        self._theme = theme or InteractiveTheme(
            enabled=bool(supports_color and supports_color())
        )
        self._agent = agent
        self._command_executor = command_executor
        self._provider_dependencies = provider_dependencies
        self._clipboard = clipboard or SystemClipboard()
        self._skills: Optional[SkillCatalog] = None
        self._active_skill: Optional[LoadedSkill] = None
        self._verbose = False
        self._diffs = diff_collector

    def run(self, root: Path, launch: InteractiveLaunch) -> int:
        """Initialize, configure, and run one private local chat session."""
        initialize_project(root)
        if self._diffs is None:
            self._diffs = GitWorkspaceDiff(root)
        if isinstance(self._terminal, PromptToolkitTerminal):
            self._terminal.configure(root)
        if not self._configure_providers(root):
            return 2
        store = ChatSessionStore(root)
        self._skills = SkillCatalog(root)
        try:
            session = self._open_session(store, launch)
        except ValueError as error:
            self._write_error(str(error))
            return 2
        self._restore_skill(session)
        self._show_banner(root, session)
        agent = self._agent or _default_agent(root, self._provider_runner(root))
        if launch.initial_prompt:
            self._chat(root, store, session, agent, launch.initial_prompt)
            session = store.load(session.session_id)
        interrupt_pending = False
        while True:
            value = self._terminal.prompt("You > ")
            if value is None or value.strip() == "/exit":
                return 0
            if value == INTERRUPT_SENTINEL:
                if interrupt_pending:
                    return 0
                interrupt_pending = True
                self._write_warning("Press Ctrl+C again to exit.")
                continue
            interrupt_pending = False
            if not value.strip():
                continue
            if value.strip() == "?":
                self._terminal.write(_hotkeys_help())
                continue
            if value.lstrip().startswith("/"):
                try:
                    should_exit, session = self._builtin(root, store, session, value)
                except ValueError as error:
                    self._write_error(str(error))
                    continue
                if should_exit:
                    return 0
                continue
            self._chat(root, store, session, agent, value)
            session = store.load(session.session_id)

    def _configure_providers(self, root: Path) -> bool:
        try:
            status = load_provider_roles_status(root)
            if status.code_provider is None and not self._select_provider(root, "code"):
                return False
            status = load_provider_roles_status(root)
            if status.test_inherited or status.test_provider is None:
                return self._select_provider(root, "test")
            return True
        except (OSError, ValueError, ProviderInstallError) as error:
            self._write_error(str(error))
            return False

    def _select_provider(self, root: Path, role: str) -> bool:
        options = tuple(_provider_option(provider) for provider in list_providers())
        selected = self._terminal.choose(
            f"Select the {role} Provider",
            options,
        )
        if selected is None:
            self._write_warning("Provider selection cancelled.")
            return False
        dependencies = self._provider_dependencies or ProviderCommandDependencies(
            sys.stdin,
            SubprocessRunner(),
            SystemCodexCommandResolver(),
        )
        result = use_provider(
            root,
            selected,
            dependencies,
            _TerminalWriter(self._terminal),
            "production-source" if role == "code" else "test-source",
        )
        if result.cancelled or result.selection is None:
            self._write_warning("Provider selection cancelled.")
            return False
        return True

    def _open_session(
        self,
        store: ChatSessionStore,
        launch: InteractiveLaunch,
    ) -> ChatSession:
        if launch.mode == "new":
            return store.create()
        if launch.mode == "latest":
            return store.latest()
        reference = launch.session_ref or self._choose_session(store)
        if reference is None:
            raise ValueError("Chat session selection was cancelled")
        return store.load(reference)

    def _choose_session(self, store: ChatSessionStore) -> Optional[str]:
        sessions = store.list()
        options = tuple(
            MenuOption(session.session_id, session.name, True) for session in sessions
        )
        if not options:
            raise ValueError("No chat session is available")
        return self._terminal.choose("Resume a chat session", options)

    def _show_banner(self, root: Path, session: ChatSession) -> None:
        status = load_project_status(root)
        providers = load_provider_roles_status(root)
        state = status.session_state or "none"
        state_text = (
            self._theme.success(state)
            if state == "DONE"
            else self._theme.warning(state)
        )
        self._terminal.write(
            f"{self._theme.accent(WHALE_LOGO)}\n"
            f"{self._theme.accent('wssagent')} "
            f"{self._theme.muted('·')} "
            f"{self._theme.text(status.project_name)}\n"
            f"{self._theme.muted('Workflow')}  {state_text}\n"
            f"{self._theme.muted('Providers')} "
            f"{self._theme.secondary(f'code {providers.code_provider}')} "
            f"{self._theme.muted('·')} "
            f"{self._theme.accent(f'test {providers.test_provider}')}\n"
            f"{self._theme.muted('Chat')}      "
            f"{self._theme.text(session.name)}\n"
            f"{self._theme.muted('Type /help for commands.')}\n"
        )
        self._update_footer(root, session)
        for message in session.messages:
            label = "You" if message.role == "user" else "Agent"
            if message.role != "event":
                body = (
                    self._theme.markdown(message.content)
                    if message.role == "assistant"
                    else self._theme.text(message.content)
                )
                color = (
                    self._theme.accent
                    if message.role == "user"
                    else self._theme.secondary
                )
                self._terminal.write(f"{color(label)} │ {body}\n")

    def _chat(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
        agent: ConversationAgent,
        value: str,
    ) -> None:
        value = sanitize_public_text(root, value)
        store.append_message(session.session_id, "user", value)
        current = store.load(session.session_id)
        try:
            status = load_project_status(root)
            workspace = WorkspaceAttachments(root)
            attachments = workspace.capture_from_text(value)
            for attachment in attachments:
                workspace.verify(attachment)
            if attachments:
                summary = ", ".join(
                    f"{attachment.path} ({attachment.size} bytes)"
                    for attachment in attachments
                )
                store.append_message(
                    session.session_id,
                    "event",
                    f"Attachments sent: {summary}.",
                )
            reply = agent.respond(
                ConversationRequest(
                    PROMPT_VERSION,
                    PROMPT_PATH.read_text(encoding="utf-8"),
                    value,
                    current.messages[:-1],
                    status.session_state,
                    attachments,
                    self._active_skill,
                )
            )
            store.append_message(session.session_id, "assistant", reply.message)
            self._terminal.write(
                f"{self._theme.secondary('Agent')} │ "
                f"{self._theme.markdown(reply.message)}\n"
            )
            self._execute_action(root, store, session, reply, value)
        except KeyboardInterrupt:
            self._write_warning("Execution cancelled.")
        except (OSError, ValueError, RequirementAnalyzerError) as error:
            self._write_error(str(error))

    def _execute_action(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
        reply: ConversationReply,
        user_message: str,
    ) -> None:
        if reply.action is None:
            return
        arguments = _action_arguments(
            root,
            reply.action,
            reply.argument,
            user_message,
        )
        if self._execute(root, store, session, arguments):
            self._run_to_gate(root, store, session)

    def _builtin(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
        value: str,
    ) -> Tuple[bool, ChatSession]:
        command, _, argument = value.strip().partition(" ")
        if command == "/help":
            self._terminal.write(_interactive_help())
        elif command == "/hotkeys":
            self._terminal.write(_hotkeys_help())
        elif command == "/copy":
            self._copy(session)
        elif command == "/diff":
            self._show_current_diff()
        elif command == "/skills":
            self._choose_skill(store, session)
        elif command == "/verbose":
            self._verbose = not self._verbose
            state = "on" if self._verbose else "off"
            self._terminal.write(
                f"{self._theme.muted('Verbose Provider events')} "
                f"{self._theme.accent(state)}.\n"
            )
        elif command == "/status":
            self._execute(root, store, session, ("status",))
        elif command in {"/feature", "/bug"}:
            if not argument.strip():
                self._write_error("A description is required.")
            elif self._execute(
                root,
                store,
                session,
                (command[1:], argument.strip()),
            ):
                self._run_to_gate(root, store, session)
        elif command == "/continue":
            state = load_project_status(root).session_state
            if state in {"REVIEW", "REFACTOR"}:
                self._run_to_gate(root, store, session)
            else:
                arguments = _advance_arguments(root)
                if self._execute(root, store, session, arguments):
                    self._run_to_gate(root, store, session)
        elif command in {"/approve", "/reject"}:
            arguments = _review_arguments(root, command[1:], argument)
            if self._execute(root, store, session, arguments):
                self._run_to_gate(root, store, session)
        elif command in {"/new", "/clear"}:
            session = store.create()
            self._terminal.write(f"New chat: {session.session_id}\n")
        elif command == "/resume":
            reference = argument.strip() or self._choose_session(store)
            if reference is not None:
                session = store.load(reference)
                self._show_banner(root, session)
        elif command in {"/rename", "/name"}:
            session = store.rename(session.session_id, argument)
            self._terminal.write(f"Chat renamed: {session.name}\n")
            self._update_footer(root, session)
        elif command in {"/exit", "/quit"}:
            return True, session
        else:
            skill_name = command.removeprefix("/")
            if not self._activate_skill(store, session, skill_name):
                self._write_error(
                    f"Unknown interactive command '{command}'. Run /help."
                )
        return False, session

    def _copy(self, session: ChatSession) -> None:
        reply = next(
            (
                message.content
                for message in reversed(session.messages)
                if message.role == "assistant"
            ),
            None,
        )
        if reply is None:
            raise ValueError("No Agent reply is available to copy")
        self._clipboard.copy(reply)
        self._terminal.write("Copied the latest Agent reply.\n")

    def _choose_skill(
        self,
        store: ChatSessionStore,
        session: ChatSession,
    ) -> None:
        if self._skills is None:
            raise ValueError("Skill catalog is unavailable")
        summaries = self._skills.list()
        if not summaries:
            raise ValueError("No Skills are available")
        options = tuple(
            MenuOption(
                summary.name,
                f"{summary.name} — {summary.description}",
                True,
            )
            for summary in summaries
        )
        selected = self._terminal.choose("Select a Skill", options)
        if selected is not None and not self._activate_skill(store, session, selected):
            raise ValueError(f"Skill could not be loaded: {selected}")

    def _activate_skill(
        self,
        store: ChatSessionStore,
        session: ChatSession,
        name: str,
    ) -> bool:
        if self._skills is None:
            return False
        try:
            self._active_skill = self._skills.load(name)
        except ValueError:
            return False
        store.append_message(
            session.session_id,
            "event",
            f"Skill activated: {name}",
        )
        self._terminal.write(f"Skill activated: {name}.\n")
        return True

    def _restore_skill(self, session: ChatSession) -> None:
        if self._skills is None:
            return
        prefix = "Skill activated: "
        for message in reversed(session.messages):
            if message.role != "event" or not message.content.startswith(prefix):
                continue
            name = message.content[len(prefix) :]
            try:
                self._active_skill = self._skills.load(name)
            except ValueError:
                self._terminal.write(f"Skill could not be restored: {name}.\n")
            return

    def _run_to_gate(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
    ) -> None:
        for _ in range(1_000):
            state = load_project_status(root).session_state
            if state in REVIEW_STATES or state == "DONE":
                return
            if state == "IMPLEMENTATION":
                if not self._execute(root, store, session, ("continue",)):
                    return
                continue
            if state == "REVIEW":
                if not self._execute(root, store, session, ("review", "semantic")):
                    return
                if not self._execute(root, store, session, ("review",)):
                    return
                continue
            if state == "REFACTOR":
                self._confirm_refactor(root, store, session)
                return
            arguments = _automatic_arguments(state)
            if arguments is None or not self._execute(root, store, session, arguments):
                return
        raise ValueError("Interactive workflow exceeded its safe step limit")

    def _confirm_refactor(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
    ) -> None:
        selected = self._terminal.choose(
            "Final refactor confirmation",
            (
                MenuOption(
                    "verify",
                    "Verify only (recommended)",
                    True,
                ),
                MenuOption(
                    "automated",
                    "Apply an automated behavior-preserving refactor",
                    True,
                ),
            ),
        )
        if selected is None:
            self._write_warning("Final verification deferred.")
            return
        arguments = (
            ("refactor", "automated") if selected == "automated" else ("refactor",)
        )
        self._execute(root, store, session, arguments)

    def _execute(
        self,
        root: Path,
        store: ChatSessionStore,
        session: ChatSession,
        arguments: Sequence[str],
    ) -> bool:
        before = (
            self._diffs.snapshot()
            if self._diffs is not None and _captures_code_diff(arguments)
            else None
        )
        executor = self._command_executor or (
            lambda command: _default_execute(
                root,
                command,
                self._provider_runner(root, command),
            )
        )
        try:
            result = executor(arguments)
        except KeyboardInterrupt:
            self._write_warning("Execution cancelled.")
            store.append_message(
                session.session_id,
                "event",
                "Workflow command cancelled.",
            )
            return False
        visible = result.stdout if result.exit_code == 0 else result.stderr
        if visible:
            rendered = (
                self._theme.markdown(visible.rstrip())
                if result.exit_code == 0
                else self._theme.error(visible.rstrip())
            )
            self._terminal.write(rendered + "\n")
        if result.exit_code == 0 and before is not None:
            self._show_changed_diff(before)
        if result.exit_code == 0:
            self._update_footer(root, session)
        event = f"Workflow command completed ({arguments[0]}; exit {result.exit_code})."
        store.append_message(session.session_id, "event", event)
        return result.exit_code == 0

    def _provider_runner(
        self,
        root: Path,
        arguments: Sequence[str] = (),
    ) -> ProcessRunner:
        config = _execution_provider_config(root, arguments)
        if config.protocol == "json-command":
            return SubprocessRunner()
        return ProviderStreamingRunner(
            config,
            root,
            SystemStreamingProcessRunner(),
            lambda event: self._render_stream_event(root, event),
        )

    def _render_stream_event(self, root: Path, event: ProviderEvent) -> None:
        rendered = render_provider_event(root, event, self._verbose)
        if rendered:
            value = rendered.rstrip()
            if event.kind == "error":
                value = self._theme.error(value)
            elif event.kind == "tool_output":
                value = self._theme.markdown(value)
            elif event.kind == "tool_finished" and event.exit_code == 0:
                value = self._theme.success(value)
            elif event.kind in {"tool_started", "progress"}:
                value = self._theme.secondary(value)
            else:
                value = self._theme.muted(value)
            self._terminal.write(value + "\n")

    def _write_error(self, message: str) -> None:
        self._terminal.write(self._theme.error(f"Error: {message}") + "\n")

    def _write_warning(self, message: str) -> None:
        self._terminal.write(self._theme.warning(message) + "\n")

    def _show_current_diff(self) -> None:
        if self._diffs is None:
            self._write_warning("No code changes.")
            return
        sections = tuple(content for _, content in self._diffs.snapshot().sections)
        if not sections:
            self._write_warning("No code changes.")
            return
        self._render_diffs("Current code changes", sections)

    def _show_changed_diff(self, before: WorkspaceDiffSnapshot) -> None:
        if self._diffs is None:
            return
        sections = self._diffs.snapshot().changed_since(before)
        if sections:
            self._render_diffs("Code changes", sections)

    def _render_diffs(
        self,
        title: str,
        sections: Tuple[str, ...],
    ) -> None:
        self._terminal.write(self._theme.accent(title) + "\n")
        for section in sections:
            self._terminal.write(self._theme.diff(section.rstrip()) + "\n")

    def _update_footer(self, root: Path, session: ChatSession) -> None:
        set_footer = getattr(self._terminal, "set_footer", None)
        if not callable(set_footer):
            return
        status = load_project_status(root)
        providers = load_provider_roles_status(root)
        set_footer(
            f"{root.resolve()} · {status.session_state or 'none'} · "
            f"{session.name} · code:{providers.code_provider} · "
            f"test:{providers.test_provider}"
        )


class _TerminalWriter(io.TextIOBase):
    def __init__(self, terminal: Terminal) -> None:
        self._terminal = terminal

    def write(self, value: str, /) -> int:
        self._terminal.write(value)
        return len(value)


def _provider_option(provider: ProviderDefinition) -> MenuOption:
    enabled = (
        provider.status == "adapter-ready"
        and provider.command is not None
        and provider.protocol is not None
    )
    reason = (
        None
        if enabled
        else (
            "custom command configuration required"
            if provider.status == "adapter-ready"
            else provider.status
        )
    )
    return MenuOption(
        provider.key,
        f"{provider.display_name} ({provider.key})",
        enabled,
        reason,
    )


def _default_agent(root: Path, runner: ProcessRunner) -> ConversationAgent:
    config = load_primary_provider_config(root)
    if config.protocol == "codex-exec":
        return CodexExecConversationAgent(config, runner, root)
    return JsonCommandConversationAgent(
        config,
        structured_cli_runner(config, runner),
    )


def _execution_provider_config(
    root: Path,
    arguments: Sequence[str],
) -> CommandAnalyzerConfig:
    if tuple(arguments) != ("continue",):
        return load_primary_provider_config(root)
    status = load_project_status(root)
    if status.current_session is None:
        return load_primary_provider_config(root)
    phase = load_current_tdd_phase(root, status.current_session)
    if phase in {None, "WRITE_TEST", "GREEN"}:
        return load_provider_config(root, "test-source")
    return load_primary_provider_config(root)


def _default_execute(
    root: Path,
    arguments: Sequence[str],
    runner: ProcessRunner,
) -> CommandResult:
    from sdd_tdd_agent.cli import main

    output = io.StringIO()
    errors = io.StringIO()
    exit_code = main(
        arguments,
        out=output,
        err=errors,
        root=root,
        runner=runner,
    )
    return CommandResult(exit_code, output.getvalue(), errors.getvalue())


def _action_arguments(
    root: Path,
    action: str,
    argument: Optional[str],
    user_message: str,
) -> Tuple[str, ...]:
    if action == "start_feature":
        return ("feature", argument or user_message)
    if action == "start_bug":
        return ("bug", argument or user_message)
    if action == "show_status":
        return ("status",)
    if action == "advance":
        return _advance_arguments(root)
    if action in {"approve", "reject"}:
        return _review_arguments(root, action, argument or "")
    raise ValueError("Conversation action is invalid")


def _advance_arguments(root: Path) -> Tuple[str, ...]:
    state = load_project_status(root).session_state
    arguments = _automatic_arguments(state)
    if arguments is not None:
        return arguments
    if state == "IMPLEMENTATION":
        return ("continue",)
    raise ValueError(f"Workflow cannot advance from state: {state or 'none'}")


def _review_arguments(
    root: Path,
    decision: str,
    argument: str,
) -> Tuple[str, ...]:
    state = load_project_status(root).session_state
    if state is None:
        raise ValueError("Workflow is not at a review gate: none")
    subject = {
        "REQUIREMENT_REVIEW": "requirement",
        "DESIGN_REVIEW": "design",
        "TASK_REVIEW": "tasks",
    }.get(state)
    if subject is None:
        raise ValueError(f"Workflow is not at a review gate: {state or 'none'}")
    if decision == "approve":
        return (subject, "approve")
    if not argument.strip():
        raise ValueError("A rejection reason is required")
    return (subject, "reject", argument.strip())


def _automatic_arguments(state: Optional[str]) -> Optional[Tuple[str, ...]]:
    if state is None:
        return None
    return {
        "ANALYSIS": ("analyze",),
        "DESIGN": ("design",),
        "TASK_BREAKDOWN": ("tasks",),
        "TEST_GENERATION": ("tests",),
    }.get(state)


def _captures_code_diff(arguments: Sequence[str]) -> bool:
    command = tuple(arguments)
    return command == ("continue",) or command == ("refactor", "automated")


def _interactive_help() -> str:
    return (
        "Commands:\n"
        "  /feature <description>  Start a feature workflow\n"
        "  /bug <description>      Start a bug workflow\n"
        "  /continue               Advance the current workflow\n"
        "  /approve                Approve the current review\n"
        "  /reject <reason>         Reject the current review\n"
        "  /copy                    Copy the latest Agent reply\n"
        "  /diff                    Show current code changes\n"
        "  /skills                  Select a project or user Skill\n"
        "  /skill-name              Activate a Skill by name\n"
        "  /verbose                 Toggle expanded Provider events\n"
        "  /status                  Show project status\n"
        "  /new                     Start a new chat\n"
        "  /clear                   Start a clean chat\n"
        "  /resume [id|name]        Resume a chat\n"
        "  /rename <name>           Rename this chat\n"
        "  /name <name>             Rename this chat (Pi alias)\n"
        "  /hotkeys                 Show keyboard shortcuts\n"
        "  /help                    Show commands\n"
        "  /exit, /quit             Exit\n"
    )


def _hotkeys_help() -> str:
    return (
        "Keyboard shortcuts:\n"
        "  Enter                    Send\n"
        "  Shift+Enter              Insert a newline\n"
        "  Tab                      Select the first completion\n"
        "  Up/Down                  History or completion navigation\n"
        "  Ctrl+C                   Clear/cancel; press twice to exit\n"
        "  Ctrl+D                   Exit when the editor is empty\n"
        "  @                        Open project file search\n"
    )
