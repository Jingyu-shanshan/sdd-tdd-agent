import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import Iterable, Optional, Tuple

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
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
    "/clear",
    "/continue",
    "/copy",
    "/diff",
    "/exit",
    "/feature",
    "/help",
    "/hotkeys",
    "/name",
    "/new",
    "/quit",
    "/reject",
    "/rename",
    "/resume",
    "/skills",
    "/status",
    "/verbose",
)
AT_PREFIX_PATTERN = re.compile(r'(?<![A-Za-z0-9._%+-])@(?:"[^"\r\n]*|[^\s]*)$')
MAX_COMPLETIONS = 20


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
        at_prefix = _at_prefix(document.text_before_cursor)
        if at_prefix is not None:
            fragment, replacement = at_prefix
            try:
                if self._path_values is None:
                    self._path_values = self._paths.paths()
            except ValueError:
                return
            for path in _ranked_paths(self._path_values, fragment):
                is_directory = path.endswith("/")
                name = PurePosixPath(path.rstrip("/")).name
                completion = f'"{path}"' if " " in path else path
                yield Completion(
                    completion,
                    start_position=-len(replacement),
                    display=f"{name}/" if is_directory else name,
                    display_meta=("directory" if is_directory else f"file · {path}"),
                )
            return
        token = document.text_before_cursor.rsplit(maxsplit=1)[-1]
        if token.startswith("/") and not document.text_before_cursor.lstrip().count(
            " "
        ):
            commands: set[str] = set(INTERACTIVE_COMMANDS)
            commands.update(f"/{skill.name}" for skill in self._skills.list())
            for command in sorted(commands):
                if command.startswith(token):
                    yield Completion(command, start_position=-len(token))


def _at_prefix(value: str) -> Optional[Tuple[str, str]]:
    match = AT_PREFIX_PATTERN.search(value)
    if match is None:
        return None
    replacement = match.group()[1:]
    fragment = replacement[1:] if replacement.startswith('"') else replacement
    return fragment.casefold(), replacement


def _ranked_paths(
    paths: Tuple[str, ...],
    query: str,
) -> Tuple[str, ...]:
    ranked = []
    for path in paths:
        score = _path_score(path, query)
        if score is None:
            continue
        ranked.append(
            (
                -score,
                0 if path.endswith("/") else 1,
                path.count("/"),
                path.casefold(),
                path,
            )
        )
    ranked.sort()
    return tuple(item[-1] for item in ranked[:MAX_COMPLETIONS])


def _path_score(path: str, query: str) -> Optional[int]:
    if not query:
        return 1
    candidate = path.casefold()
    name = PurePosixPath(path.rstrip("/")).name.casefold()
    if name == query:
        return 1_000
    if name.startswith(query):
        return 900
    if query in name:
        return 700 - name.index(query)
    if candidate.startswith(query):
        return 600
    if query in candidate:
        return 500 - candidate.index(query)
    position = -1
    gaps = 0
    for character in query:
        next_position = candidate.find(character, position + 1)
        if next_position < 0:
            return None
        if position >= 0:
            gaps += next_position - position - 1
        position = next_position
    return max(1, 300 - gaps)


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

    @bindings.add("tab", eager=True)
    def _select_completion(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if buffer.complete_state is not None:
            buffer.complete_next()
            return
        if buffer.completer is None:
            return
        completions = buffer.completer.get_completions(
            buffer.document,
            CompleteEvent(completion_requested=True),
        )
        first = next(iter(completions), None)
        if first is not None:
            buffer.apply_completion(first)

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

    @bindings.add("c-j")
    def _ctrl_j(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    @bindings.add(Keys.BracketedPaste, eager=True)
    def _paste(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text(pastes.fold(event.data))

    return bindings
