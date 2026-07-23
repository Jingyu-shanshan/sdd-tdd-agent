from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
    structured_cli_runner,
)
from sdd_tdd_agent.provider_registry import (
    get_provider,
    load_provider_selection,
    select_provider,
)
from sdd_tdd_agent.provider_tools import ProviderInstaller


PI_COMMAND = (
    "pi",
    "-p",
    "--no-session",
    "--no-tools",
    "--no-context-files",
    "--no-extensions",
    "--no-skills",
    "--no-prompt-templates",
    "--no-approve",
)


class RecordingRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[Tuple[str, ...], str, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, stdin, timeout_seconds))
        return self.result


class PiLocator:
    def locate(self, executable: str) -> Optional[str]:
        assert executable == "pi"
        return "/home/user/.local/bin/pi"


class PiInstallRunner:
    def __init__(self) -> None:
        self.commands: list[Tuple[str, ...]] = []

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
            return ProcessResult(0, "", "")
        return ProcessResult(0, "pi 0.73.1\n", "")


def _write_config(root: Path) -> Path:
    workspace = root / ".agent"
    workspace.mkdir()
    path = workspace / "config.yml"
    path.write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 45
""",
        encoding="utf-8",
    )
    return path


def test_should_register_selectable_pi_provider() -> None:
    provider = get_provider("pi")

    assert provider.status == "adapter-ready"
    assert provider.platforms == ("macos", "linux-mint")
    assert provider.protocol == "pi-exec"
    assert provider.command == ("pi",)
    assert provider.install_plan is not None
    assert provider.install_plan.source_url == "https://pi.dev/install.sh"


def test_should_run_pi_in_isolated_print_mode() -> None:
    delegate = RecordingRunner(ProcessResult(0, '{"answer":"ok"}\n', "ignored"))
    config = CommandAnalyzerConfig(("pi",), 41, "pi-exec")
    runner = structured_cli_runner(config, delegate)

    result = runner.run(config.command, '{"request":"typed"}', 41)

    assert delegate.calls == [(PI_COMMAND, '{"request":"typed"}', 41)]
    assert result == ProcessResult(0, '{"answer": "ok"}', "")


def test_should_reject_invalid_pi_output_without_leaking_content() -> None:
    delegate = RecordingRunner(ProcessResult(0, "SECRET", "SECRET"))
    config = CommandAnalyzerConfig(("pi",), 30, "pi-exec")

    with pytest.raises(RequirementAnalyzerError) as captured:
        structured_cli_runner(config, delegate).run(config.command, "SECRET", 30)

    assert "SECRET" not in str(captured.value)


def test_should_select_pi_in_project_config(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    selection = select_provider(tmp_path, "pi")

    assert selection.provider_key == "pi"
    assert load_provider_selection(tmp_path).provider_key == "pi"
    assert (
        config_path.read_text(encoding="utf-8")
        == """\
requirement_analyzer_protocol: pi-exec
requirement_analyzer_command:
  - "pi"
requirement_analyzer_timeout_seconds: 45
"""
    )


def test_should_install_pi_from_official_script() -> None:
    runner = PiInstallRunner()
    installer = ProviderInstaller(runner, PiLocator(), 120)

    result = installer.install("pi")

    script_path = runner.commands[0][3]
    assert runner.commands == [
        ("curl", "-fsSL", "--output", script_path, "https://pi.dev/install.sh"),
        ("sh", script_path),
        ("/home/user/.local/bin/pi", "--version"),
    ]
    assert result.provider_key == "pi"
    assert result.version == "pi 0.73.1"
