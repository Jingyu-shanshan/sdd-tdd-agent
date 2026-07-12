import io
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies


class InstalledLocator:
    def locate(self, executable: str) -> Optional[str]:
        return "/usr/local/bin/codex"


class HealthyRunner:
    def __init__(self) -> None:
        self.timeout_seconds: Optional[float] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.timeout_seconds = timeout_seconds
        return ProcessResult(0, "codex-cli 1.2.3\n", "")


def test_should_diagnose_selected_provider_through_cli(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 45
""",
        encoding="utf-8",
    )
    output = io.StringIO()
    runner = HealthyRunner()
    dependencies = ProviderCommandDependencies(
        input=io.StringIO(),
        runner=runner,
        locator=InstalledLocator(),
    )

    exit_code = main(
        ["provider", "doctor"],
        out=output,
        root=tmp_path,
        provider_dependencies=dependencies,
    )

    assert exit_code == 0
    assert runner.timeout_seconds == 45
    assert (
        output.getvalue()
        == """\
Provider: codex
Adapter status: adapter-ready
CLI status: installed
Version: codex-cli 1.2.3
"""
    )
