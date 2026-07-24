import io
from pathlib import Path

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.interactive_shell import InteractiveLaunch


class RecordingInteractiveShell:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, InteractiveLaunch]] = []

    def run(self, root: Path, launch: InteractiveLaunch) -> int:
        self.calls.append((root, launch))
        return 0


def test_should_start_new_interactive_session_for_empty_tty_command(
    tmp_path: Path,
) -> None:
    shell = RecordingInteractiveShell()

    exit_code = main([], root=tmp_path, interactive_shell=shell)

    assert exit_code == 0
    assert shell.calls == [(tmp_path, InteractiveLaunch("new"))]


def test_should_keep_help_for_empty_non_interactive_command(tmp_path: Path) -> None:
    output = io.StringIO()

    exit_code = main([], root=tmp_path, out=output)

    assert exit_code == 0
    assert output.getvalue().startswith("Usage: wssagent <command>")


def test_should_route_resume_and_initial_prompt_to_interactive_shell(
    tmp_path: Path,
) -> None:
    shell = RecordingInteractiveShell()

    assert main(["-c"], root=tmp_path, interactive_shell=shell) == 0
    assert (
        main(
            ["--resume", "export-flow"],
            root=tmp_path,
            interactive_shell=shell,
        )
        == 0
    )
    assert (
        main(
            ["Build PDF export"],
            root=tmp_path,
            interactive_shell=shell,
        )
        == 0
    )

    assert shell.calls == [
        (tmp_path, InteractiveLaunch("latest")),
        (tmp_path, InteractiveLaunch("resume", session_ref="export-flow")),
        (tmp_path, InteractiveLaunch("new", initial_prompt="Build PDF export")),
    ]
