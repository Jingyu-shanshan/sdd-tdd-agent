from pathlib import Path

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from sdd_tdd_agent.composer import WorkspaceCompleter
from sdd_tdd_agent.interactive_shell import PromptToolkitTerminal


def test_should_complete_safe_project_paths_after_at(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")
    completer = WorkspaceCompleter(tmp_path)

    completions = tuple(
        completer.get_completions(
            Document("@src/ap", cursor_position=7),
            CompleteEvent(),
        )
    )

    assert [(item.text, item.start_position) for item in completions] == [
        ("src/app.py", -6)
    ]


def test_should_support_backslash_enter_multiline_input(tmp_path: Path) -> None:
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("first\\\rsecond\r")

        assert terminal.prompt("You > ") == "first\nsecond"


def test_should_support_shift_enter_multiline_input(tmp_path: Path) -> None:
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("first\x1b\rsecond\r")

        assert terminal.prompt("You > ") == "first\nsecond"


def test_should_fold_long_bracketed_paste_but_submit_full_text(
    tmp_path: Path,
) -> None:
    pasted = "x" * 10_001
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text(f"\x1b[200~{pasted}\x1b[201~\r")

        assert terminal.prompt("You > ") == pasted


def test_should_recall_previous_input_with_up_arrow(tmp_path: Path) -> None:
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("first request\r")
        assert terminal.prompt("You > ") == "first request"
        pipe.send_text("\x1b[A\r")
        assert terminal.prompt("You > ") == "first request"
