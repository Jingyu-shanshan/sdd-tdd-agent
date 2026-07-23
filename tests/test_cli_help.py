import io
import subprocess
import sys
from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main


def test_should_show_global_help_without_project_workspace(tmp_path: Path) -> None:
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(["--help"], out=output, err=error_output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Usage: wssagent <command> [options]\n")
    assert "provider     List, inspect, diagnose, or select Agent Providers." in (
        output.getvalue()
    )
    assert "wssagent provider list" in output.getvalue()
    assert "wssagent <command> --help" in output.getvalue()
    assert error_output.getvalue() == ""
    assert not (tmp_path / ".agent").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["help"],
        ["-h"],
    ],
)
def test_should_make_global_help_easy_to_discover(
    tmp_path: Path,
    arguments: list[str],
) -> None:
    output = io.StringIO()

    exit_code = main(arguments, out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Usage: wssagent <command> [options]\n")


@pytest.mark.parametrize(
    "arguments",
    [
        ["provider", "--help"],
        ["provider", "use", "--help"],
        ["help", "provider"],
    ],
)
def test_should_show_provider_queries_and_selection_help(
    tmp_path: Path,
    arguments: list[str],
) -> None:
    output = io.StringIO()

    exit_code = main(arguments, out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Usage: wssagent provider <command>")
    assert "wssagent provider list" in output.getvalue()
    assert "wssagent provider doctor [provider]" in output.getvalue()
    assert "--for test-source|production-source" in output.getvalue()


def test_should_suggest_close_command_for_typo(tmp_path: Path) -> None:
    error_output = io.StringIO()

    exit_code = main(["providr", "list"], err=error_output, root=tmp_path)

    assert exit_code == 2
    assert error_output.getvalue() == (
        "Error: Unknown command 'providr'. Did you mean 'provider'?\n"
        "Run 'wssagent --help' to list available commands.\n"
    )


def test_should_point_invalid_subcommand_to_group_help(tmp_path: Path) -> None:
    error_output = io.StringIO()

    exit_code = main(
        ["provider", "unsupported"],
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 2
    assert error_output.getvalue() == (
        "Error: Invalid arguments for command 'provider'.\n"
        "Run 'wssagent provider --help' for usage.\n"
    )


def test_should_reject_extra_arguments_in_exact_command(tmp_path: Path) -> None:
    error_output = io.StringIO()

    exit_code = main(["hello", "unexpected"], err=error_output, root=tmp_path)

    assert exit_code == 2
    assert error_output.getvalue() == (
        "Error: Invalid arguments for command 'hello'.\n"
        "Run 'wssagent hello --help' for usage.\n"
    )


def test_should_render_uncaught_user_error_without_traceback(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sdd_tdd_agent", "feature"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "Error: Feature description must not be empty\n"
