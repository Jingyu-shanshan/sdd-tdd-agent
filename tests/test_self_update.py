import io
from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult, RequirementAnalyzerError
from sdd_tdd_agent.self_update import (
    MAX_METADATA_BYTES,
    UPDATE_COMMAND,
    fetch_latest_version,
    installed_version,
    load_latest_version,
    parse_project_version,
    render_update_notice,
    write_update_notice,
)


class UpdateRunner:
    def __init__(self, returncode: int = 0, start_error: bool = False) -> None:
        self.returncode = returncode
        self.start_error = start_error
        self.commands: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        if self.start_error:
            raise RequirementAnalyzerError("unavailable")
        return ProcessResult(self.returncode, "", "")


def test_should_parse_project_version_and_render_yellow_update_notice() -> None:
    assert installed_version() == "0.3.1"
    latest = parse_project_version(
        '[build-system]\nrequires = []\n\n[project]\nversion = "0.3.0"\n'
    )

    notice = render_update_notice("0.2.1", latest)

    assert notice == (
        "\x1b[33mUpdate available: wssagent 0.2.1 -> 0.3.0. "
        "Run 'wssagent update'.\x1b[0m\n"
    )
    assert render_update_notice("0.3.0", latest) == ""


@pytest.mark.parametrize(
    "content",
    [
        '[project]\nversion = "invalid"\n',
        "[project]\nversion = 3\n",
        '[project]\nname = "missing"\n[tool.ruff]\n',
    ],
)
def test_should_reject_invalid_remote_project_version(content: str) -> None:
    with pytest.raises(ValueError):
        parse_project_version(content)


def test_should_bound_downloaded_project_metadata() -> None:
    def download(url: str, limit: int) -> bytes:
        assert limit == MAX_METADATA_BYTES
        return b"x" * (limit + 1)

    with pytest.raises(ValueError, match="too large"):
        fetch_latest_version(download)


def test_should_cache_latest_version(tmp_path: Path) -> None:
    cache_path = tmp_path / "latest-version"
    calls = 0

    def fetch() -> str:
        nonlocal calls
        calls += 1
        return "0.3.0"

    first = load_latest_version(cache_path, fetch, now=1000)
    second = load_latest_version(cache_path, fetch, now=1001)

    assert first == "0.3.0"
    assert second == "0.3.0"
    assert calls == 1


def test_should_continue_when_update_cache_cannot_be_written(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    latest = load_latest_version(
        blocked_parent / "latest-version",
        lambda: "0.3.0",
        now=1000,
    )

    assert latest == "0.3.0"


def test_should_write_notice_and_ignore_check_failure() -> None:
    output = io.StringIO()
    write_update_notice(output, lambda: "0.2.1", lambda: "0.3.0")

    def fail() -> str:
        raise OSError("offline")

    write_update_notice(output, lambda: "0.2.1", fail)

    assert "\x1b[33mUpdate available" in output.getvalue()


def test_should_update_installed_tool_without_uninstalling() -> None:
    output = io.StringIO()
    error_output = io.StringIO()
    runner = UpdateRunner()

    exit_code = main(
        ["update"],
        out=output,
        err=error_output,
        runner=runner,
    )

    assert exit_code == 0
    assert runner.commands == [UPDATE_COMMAND]
    assert output.getvalue() == "wssagent updated successfully.\n"
    assert error_output.getvalue() == ""


def test_should_report_update_failure() -> None:
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["update"],
        out=output,
        err=error_output,
        runner=UpdateRunner(returncode=1),
    )

    assert exit_code == 2
    assert output.getvalue() == ""
    assert error_output.getvalue() == (
        "Error: wssagent update failed; verify uv is installed and the network is "
        "available\n"
    )


def test_should_report_missing_uv() -> None:
    error_output = io.StringIO()

    exit_code = main(
        ["update"],
        err=error_output,
        runner=UpdateRunner(start_error=True),
    )

    assert exit_code == 2
    assert error_output.getvalue() == (
        "Error: wssagent update could not start; verify uv is installed\n"
    )


@pytest.mark.parametrize("arguments", [["update", "--help"], ["help", "update"]])
def test_should_show_update_help(arguments: list[str]) -> None:
    output = io.StringIO()

    exit_code = main(arguments, out=output)

    assert exit_code == 0
    assert output.getvalue().startswith("Usage: wssagent update\n")
