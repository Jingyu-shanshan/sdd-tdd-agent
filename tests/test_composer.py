from pathlib import Path

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from sdd_tdd_agent.composer import WorkspaceCompleter
from sdd_tdd_agent.interactive_shell import (
    INTERRUPT_SENTINEL,
    PromptToolkitTerminal,
)


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


def test_should_show_ranked_file_menu_for_empty_at_prefix(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")

    completions = tuple(
        WorkspaceCompleter(tmp_path).get_completions(
            Document("@", cursor_position=1),
            CompleteEvent(),
        )
    )

    assert [item.text for item in completions] == [
        "src/",
        "README.md",
        "src/app.py",
    ]
    assert [item.display_text for item in completions] == [
        "src/",
        "README.md",
        "app.py",
    ]
    assert [item.display_meta_text for item in completions] == [
        "directory",
        "file · README.md",
        "file · src/app.py",
    ]


def test_should_fuzzy_match_and_quote_attachment_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source files"
    source.mkdir()
    (source / "agent_config.py").write_text("pass\n", encoding="utf-8")
    completer = WorkspaceCompleter(tmp_path)

    completions = tuple(
        completer.get_completions(
            Document("@agcfg", cursor_position=6),
            CompleteEvent(),
        )
    )

    assert [item.text for item in completions] == ['"source files/agent_config.py"']
    assert completions[0].start_position == -5


def test_should_apply_visible_at_file_completion_from_editor(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("pass\n", encoding="utf-8")

    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("@\t\r")

        assert terminal.prompt("You > ") == "@src/"


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


def test_should_support_ctrl_j_multiline_input(tmp_path: Path) -> None:
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("first\x0asecond\r")

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


def test_should_return_interrupt_signal_on_ctrl_c(tmp_path: Path) -> None:
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(input=pipe, output=DummyOutput())
        terminal.configure(tmp_path)
        pipe.send_text("\x03")

        assert terminal.prompt("You > ") == INTERRUPT_SENTINEL
