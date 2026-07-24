import io
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.provider_tools import ProviderCommandDependencies


class UnexpectedRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Provider selection must not run a process")


class UnexpectedLocator:
    def locate(self, executable: str) -> Optional[str]:
        raise AssertionError("Non-interactive selection must not locate a CLI")


def _dependencies() -> ProviderCommandDependencies:
    return ProviderCommandDependencies(
        input=io.StringIO(),
        runner=UnexpectedRunner(),
        locator=UnexpectedLocator(),
    )


def test_should_explain_that_provider_selection_requires_init(tmp_path: Path) -> None:
    error_output = io.StringIO()

    exit_code = main(
        ["provider", "use", "claude-code", "--for", "test-source"],
        err=error_output,
        root=tmp_path,
        provider_dependencies=_dependencies(),
    )

    assert exit_code == 2
    assert error_output.getvalue() == (
        "Error: Project is not initialized; run 'wssagent init' in the project root\n"
    )


def test_should_select_role_provider_immediately_after_init(tmp_path: Path) -> None:
    output = io.StringIO()
    error_output = io.StringIO()
    initialize_project(tmp_path)

    exit_code = main(
        ["provider", "use", "claude-code", "--for", "test-source"],
        out=output,
        err=error_output,
        root=tmp_path,
        provider_dependencies=_dependencies(),
    )

    config = (tmp_path / ".agent" / "config.yml").read_text(encoding="utf-8")
    assert exit_code == 0
    assert output.getvalue() == "Selected provider for test-source: claude-code\n"
    assert error_output.getvalue() == ""
    assert "requirement_analyzer_protocol: codex-exec\n" in config
    assert 'requirement_analyzer_command:\n  - "codex"\n' in config
    assert "requirement_analyzer_timeout_seconds: 300\n" in config
    assert "test_source_provider: claude-code\n" in config
