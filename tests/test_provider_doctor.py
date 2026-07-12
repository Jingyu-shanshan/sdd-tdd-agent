from typing import Optional, Tuple

from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import (
    ProviderDoctor,
    render_provider_diagnostic,
)


class FixedLocator:
    def __init__(self, executable: Optional[str]) -> None:
        self.executable = executable

    def locate(self, executable: str) -> Optional[str]:
        return self.executable


class VersionRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        return self.result


def test_should_report_installed_provider_version() -> None:
    runner = VersionRunner(ProcessResult(0, "codex-cli 1.2.3\n", ""))
    doctor = ProviderDoctor(
        runner=runner,
        locator=FixedLocator("/usr/local/bin/codex"),
        timeout_seconds=30,
    )

    diagnostic = doctor.diagnose("codex")

    assert runner.command == ("/usr/local/bin/codex", "--version")
    assert diagnostic.cli_status == "installed"
    assert diagnostic.version == "codex-cli 1.2.3"
    assert render_provider_diagnostic(diagnostic) == """\
Provider: codex
Adapter status: adapter-ready
CLI status: installed
Version: codex-cli 1.2.3
"""


def test_should_report_missing_provider_without_running_version() -> None:
    runner = VersionRunner(ProcessResult(0, "unexpected", ""))
    doctor = ProviderDoctor(
        runner=runner,
        locator=FixedLocator(None),
        timeout_seconds=30,
    )

    diagnostic = doctor.diagnose("codex")

    assert runner.command is None
    assert diagnostic.cli_status == "missing"
    assert diagnostic.version is None


def test_should_report_planned_provider_without_executable_lookup() -> None:
    runner = VersionRunner(ProcessResult(0, "unexpected", ""))
    doctor = ProviderDoctor(
        runner=runner,
        locator=FixedLocator("unexpected"),
        timeout_seconds=30,
    )

    diagnostic = doctor.diagnose("claude-code")

    assert runner.command is None
    assert diagnostic.adapter_status == "planned"
    assert diagnostic.cli_status == "not-checked"
