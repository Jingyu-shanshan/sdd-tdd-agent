from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CodexExecRequirementAnalyzer,
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.requirement_analysis import RequirementAnalysisRequest


def missing_path_lookup(executable: str) -> Optional[str]:
    return None


def test_should_fall_back_to_installed_chatgpt_codex_when_path_is_missing(
    tmp_path: Path,
) -> None:
    bundled_codex = tmp_path / "ChatGPT.app" / "Contents" / "Resources" / "codex"
    bundled_codex.parent.mkdir(parents=True)
    bundled_codex.write_text("executable", encoding="utf-8")
    bundled_codex.chmod(0o700)
    resolver = SystemCodexCommandResolver(
        path_lookup=missing_path_lookup,
        fallback_paths=(bundled_codex,),
    )

    executable = resolver.resolve("codex")

    assert executable == str(bundled_codex)


def test_should_preserve_custom_command_when_path_is_missing(tmp_path: Path) -> None:
    bundled_codex = tmp_path / "codex"
    bundled_codex.write_text("executable", encoding="utf-8")
    bundled_codex.chmod(0o700)
    resolver = SystemCodexCommandResolver(
        path_lookup=missing_path_lookup,
        fallback_paths=(bundled_codex,),
    )

    assert resolver.resolve("custom-codex") == "custom-codex"


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "/Applications/ChatGPT.app/Contents/Resources/codex"


class RecordingFailureRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        return ProcessResult(returncode=1, stdout="", stderr="")


def test_should_use_resolved_codex_executable(tmp_path: Path) -> None:
    runner = RecordingFailureRunner()
    analyzer = CodexExecRequirementAnalyzer(
        config=CommandAnalyzerConfig(command=("codex",), timeout_seconds=10),
        runner=runner,
        workspace=tmp_path,
        command_resolver=FixedResolver(),
    )
    request = RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="Analyze requirements.",
        user_request="Support PDF export",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )

    with pytest.raises(RequirementAnalyzerError):
        analyzer.analyze(request)

    assert runner.command is not None
    assert runner.command[0] == "/Applications/ChatGPT.app/Contents/Resources/codex"
