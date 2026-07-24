from pathlib import Path
from typing import Iterable, Optional, Tuple

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys

from sdd_tdd_agent.skill_catalog import SkillCatalog
from sdd_tdd_agent.workspace_attachments import WorkspaceAttachments


LONG_PASTE_CHARACTERS = 10_000
INTERACTIVE_COMMANDS = (
    "/approve",
    "/bug",
    "/continue",
    "/copy",
    "/exit",
    "/feature",
    "/help",
    "/new",
    "/reject",
    "/rename",
    "/resume",
    "/skills",
    "/status",
    "/verbose",
)


class WorkspaceCompleter(Completer):
    """Complete safe workspace paths, commands, and discovered Skills."""

    def __init__(self, root: Path) -> None:
        self._paths = WorkspaceAttachments(root)
        self._skills = SkillCatalog(root)
        self._path_values: Optional[Tuple[str, ...]] = None

    def get_completions(
        self,
        document: Document,
        complete_event: object,
    ) -> Iterable[Completion]:
        """Yield deterministic matches for the token before the cursor."""
        del complete_event
        token = document.text_before_cursor.rsplit(maxsplit=1)[-1]
        if token.startswith("@"):
            fragment = token[1:]
            try:
                if self._path_values is None:
                    self._path_values = self._paths.paths()
            except ValueError:
                return
            for path in self._path_values:
                if path.startswith(fragment):
                    yield Completion(path, start_position=-len(fragment))
            return
        if token.startswith("/") and not document.text_before_cursor.lstrip().count(
            " "
        ):
            commands: set[str] = set(INTERACTIVE_COMMANDS)
            commands.update(f"/{skill.name}" for skill in self._skills.list())
            for command in sorted(commands):
                if command.startswith(token):
                    yield Completion(command, start_position=-len(token))


class PasteStore:
    """Keep large bracketed paste text in memory behind visible placeholders."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def fold(self, value: str) -> str:
        """Return original short text or one stable folded placeholder."""
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        if len(normalized) <= LONG_PASTE_CHARACTERS:
            return normalized
        placeholder = (
            f"[Pasted text #{len(self._values) + 1}: {len(normalized)} characters]"
        )
        self._values[placeholder] = normalized
        return placeholder

    def expand(self, value: str) -> str:
        """Restore all placeholders and clear their in-memory source."""
        expanded = value
        for placeholder, content in self._values.items():
            expanded = expanded.replace(placeholder, content)
        self._values.clear()
        return expanded


def composer_bindings(pastes: PasteStore) -> KeyBindings:
    """Build multiline and long-paste bindings for one PromptSession."""
    bindings = KeyBindings()

    @bindings.add("enter")
    def _enter(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if buffer.document.is_cursor_at_the_end and buffer.text.endswith("\\"):
            buffer.delete_before_cursor()
            buffer.insert_text("\n")
            return
        buffer.validate_and_handle()

    @bindings.add("escape", "enter")
    def _shift_enter(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    @bindings.add(Keys.BracketedPaste, eager=True)
    def _paste(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text(pastes.fold(event.data))

    return bindings
