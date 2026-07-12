import io
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies


class TtyInput(io.StringIO):
    def isatty(self) -> bool:
        return True


class MissingLocator:
    def locate(self, executable: str) -> Optional[str]:
        return None


class UnexpectedRunner:
    def __init__(self) -> None:
        self.called = False

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.called = True
        return ProcessResult(0, "", "")


def test_should_reject_install_on_unsupported_platform_without_download(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    config_path = workspace / "config.yml"
    original = """\
requirement_analyzer_protocol: json-command
requirement_analyzer_command:
  - "custom-bridge"
requirement_analyzer_timeout_seconds: 45
"""
    config_path.write_text(original, encoding="utf-8")
    output = io.StringIO()
    error_output = io.StringIO()
    runner = UnexpectedRunner()
    dependencies = ProviderCommandDependencies(
        input=TtyInput("yes\n"),
        runner=runner,
        locator=MissingLocator(),
        platform="win32",
    )

    exit_code = main(
        ["provider", "use", "codex"],
        out=output,
        err=error_output,
        root=tmp_path,
        provider_dependencies=dependencies,
    )

    assert exit_code == 2
    assert output.getvalue() == ""
    assert error_output.getvalue() == (
        "Error: Provider installer is not supported on this platform\n"
    )
    assert runner.called is False
    assert config_path.read_text(encoding="utf-8") == original
