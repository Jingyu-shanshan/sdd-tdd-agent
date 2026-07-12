import io
import json
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies


ORIGINAL_CONFIG = """\
requirement_analyzer_protocol: json-command
requirement_analyzer_command:
  - "custom-bridge"
requirement_analyzer_timeout_seconds: 45
"""


class TtyInput(io.StringIO):
    def isatty(self) -> bool:
        return True


class SequenceLocator:
    def __init__(self, locations: List[Optional[str]]) -> None:
        self.locations = locations

    def locate(self, executable: str) -> Optional[str]:
        return self.locations.pop(0)


class InstallRunner:
    def __init__(self, install_returncode: int = 0) -> None:
        self.install_returncode = install_returncode
        self.commands: List[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        if command[0] == "curl":
            script = Path(command[command.index("--output") + 1])
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            return ProcessResult(0, "", "")
        if command[0] == "sh":
            return ProcessResult(self.install_returncode, "SECRET", "SECRET")
        return ProcessResult(0, "codex-cli 2.0.0\n", "")


def _write_workspace(root: Path) -> tuple[Path, Path]:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    config_path = workspace / "config.yml"
    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    state_path = session / "state.json"
    state_path.write_text(
        json.dumps({"session_id": "feature-1", "state": "REQUIREMENT_REVIEW"}),
        encoding="utf-8",
    )
    return config_path, state_path


def _run_use(
    root: Path,
    user_input: io.StringIO,
    runner: InstallRunner,
    locator: SequenceLocator,
) -> tuple[int, str, str]:
    output = io.StringIO()
    error_output = io.StringIO()
    dependencies = ProviderCommandDependencies(user_input, runner, locator)
    exit_code = main(
        ["provider", "use", "codex"],
        out=output,
        err=error_output,
        root=root,
        provider_dependencies=dependencies,
    )
    return exit_code, output.getvalue(), error_output.getvalue()


def test_should_install_verify_and_select_after_confirmation(tmp_path: Path) -> None:
    config_path, state_path = _write_workspace(tmp_path)
    original_state = state_path.read_text(encoding="utf-8")
    runner = InstallRunner()

    exit_code, output, error = _run_use(
        tmp_path,
        TtyInput("yes\n"),
        runner,
        SequenceLocator([None, "/home/user/.local/bin/codex"]),
    )

    assert exit_code == 0
    assert output == (
        "Provider CLI 'codex' was not found. Install the current stable CLI "
        "from the official source? [y/N] "
        "Installed provider CLI: codex (codex-cli 2.0.0)\n"
        "Selected provider: codex\n"
    )
    assert error == ""
    assert [command[0] for command in runner.commands] == ["curl", "sh", "/home/user/.local/bin/codex"]
    assert "requirement_analyzer_protocol: codex-exec" in config_path.read_text(
        encoding="utf-8"
    )
    assert state_path.read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize("answer", ["\n", "n\n", "no\n", "unexpected\n"])
def test_should_cancel_without_install_or_selection(
    tmp_path: Path,
    answer: str,
) -> None:
    config_path, state_path = _write_workspace(tmp_path)
    original_state = state_path.read_text(encoding="utf-8")
    runner = InstallRunner()

    exit_code, output, error = _run_use(
        tmp_path,
        TtyInput(answer),
        runner,
        SequenceLocator([None]),
    )

    assert exit_code == 2
    assert output.endswith("[y/N] Provider selection cancelled.\n")
    assert error == ""
    assert runner.commands == []
    assert config_path.read_text(encoding="utf-8") == ORIGINAL_CONFIG
    assert state_path.read_text(encoding="utf-8") == original_state


def test_should_preserve_config_when_installation_fails(tmp_path: Path) -> None:
    config_path, state_path = _write_workspace(tmp_path)
    original_state = state_path.read_text(encoding="utf-8")

    exit_code, output, error = _run_use(
        tmp_path,
        TtyInput("y\n"),
        InstallRunner(install_returncode=19),
        SequenceLocator([None]),
    )

    assert exit_code == 2
    assert output.endswith("[y/N] ")
    assert error == "Error: Provider installer execution failed\n"
    assert "SECRET" not in error
    assert config_path.read_text(encoding="utf-8") == ORIGINAL_CONFIG
    assert state_path.read_text(encoding="utf-8") == original_state


def test_should_never_install_during_non_interactive_selection(
    tmp_path: Path,
) -> None:
    config_path, _ = _write_workspace(tmp_path)
    runner = InstallRunner()

    exit_code, output, error = _run_use(
        tmp_path,
        io.StringIO("yes\n"),
        runner,
        SequenceLocator([]),
    )

    assert exit_code == 0
    assert output == "Selected provider: codex\n"
    assert error == ""
    assert runner.commands == []
    assert "requirement_analyzer_protocol: codex-exec" in config_path.read_text(
        encoding="utf-8"
    )
