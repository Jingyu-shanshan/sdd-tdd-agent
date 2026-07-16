import json
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.production_source_adapter import (
    CodexExecProductionSourceGenerator,
    JsonCommandProductionSourceGenerator,
    ProductionSourceGeneratorError,
)
from sdd_tdd_agent.production_source_generation import (
    GeneratedProductionSource,
    ProductionSourceGenerationRequest,
    load_production_source_generation_request,
)
from sdd_tdd_agent.production_source_workspace import (
    WorkspaceProductionSourceCollector,
)
from tests.production_source_support import (
    GENERATED_CONTENT,
    create_red_workspace,
)


def _response() -> dict[str, str]:
    return {
        "test_id": "TC1",
        "file_path": "src/export.ts",
        "content": GENERATED_CONTENT,
    }


def _request(root: Path) -> ProductionSourceGenerationRequest:
    sources = WorkspaceProductionSourceCollector().collect(root)
    return load_production_source_generation_request(root, "feature-1", sources)


class JsonRunner:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        return ProcessResult(self.returncode, self.stdout, "SECRET")


class CodexRunner:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.command: Optional[Tuple[str, ...]] = None
        self.isolated_root: Optional[Path] = None
        self.existed_during_run = False

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.isolated_root = Path(command[command.index("--cd") + 1])
        self.existed_during_run = self.isolated_root.is_dir()
        assert self.isolated_root != self.project_root
        assert self.project_root not in self.isolated_root.parents
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_response()), encoding="utf-8")
        return ProcessResult(0, "", "")


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "resolved-codex"


def test_should_exchange_strict_blind_json_payload(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    runner = JsonRunner(json.dumps(_response()))
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider", "--json"), 12.0),
        runner,
    )

    generated = generator.generate(_request(tmp_path))

    assert generated == GeneratedProductionSource(
        "TC1",
        "src/export.ts",
        GENERATED_CONTENT,
    )
    assert runner.command == ("provider", "--json")
    assert runner.stdin is not None
    payload = json.loads(runner.stdin)
    assert set(payload) == {
        "prompt_version",
        "prompt",
        "current_test",
        "current_test_source",
        "production_sources",
        "compile_output",
        "test_output",
    }
    serialized = runner.stdin
    for forbidden in (
        "REQUIREMENT-SENTINEL",
        "DESIGN-SENTINEL",
        "TASK-SENTINEL",
        "future_tests",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "stdout",
    [
        "not-json",
        "[]",
        json.dumps({"test_id": "TC1"}),
        json.dumps({**_response(), "extra": "value"}),
        json.dumps({**_response(), "content": 4}),
    ],
)
def test_should_reject_invalid_json_provider_result(
    tmp_path: Path,
    stdout: str,
) -> None:
    create_red_workspace(tmp_path)
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        JsonRunner(stdout),
    )

    with pytest.raises(ProductionSourceGeneratorError):
        generator.generate(_request(tmp_path))


def test_should_redact_provider_failure_content(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        JsonRunner("SECRET", returncode=9),
    )

    with pytest.raises(ProductionSourceGeneratorError) as captured:
        generator.generate(_request(tmp_path))

    assert str(captured.value) == "Production source generator failed with exit code 9"
    assert "SECRET" not in str(captured.value)


def test_should_reject_missing_current_test_source(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    request = replace(
        request,
        context=replace(request.context, current_test_source=None),
    )
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        JsonRunner(json.dumps(_response())),
    )

    with pytest.raises(ProductionSourceGeneratorError, match="missing"):
        generator.generate(request)


def test_should_translate_semantically_invalid_provider_result(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    response = {**_response(), "test_id": "TC2"}
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider",), 12.0),
        JsonRunner(json.dumps(response)),
    )

    with pytest.raises(ProductionSourceGeneratorError, match="identifier"):
        generator.generate(_request(tmp_path))


def test_should_run_codex_in_external_ephemeral_workspace(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    runner = CodexRunner(tmp_path)
    generator = CodexExecProductionSourceGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        runner,
        tmp_path / "external-context",
        command_resolver=FixedResolver(),
    )

    generated = generator.generate(_request(tmp_path))

    assert generated.file_path == "src/export.ts"
    assert runner.command is not None
    assert runner.command[0:2] == ("resolved-codex", "exec")
    assert runner.existed_during_run is True
    assert runner.isolated_root is not None
    assert not runner.isolated_root.exists()


def test_should_reject_multiple_codex_command_tokens(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecProductionSourceGenerator(
            CommandAnalyzerConfig(("codex", "extra"), 12.0, "codex-exec"),
            JsonRunner(""),
            tmp_path,
        )


def test_should_report_codex_failure_without_output_content(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    generator = CodexExecProductionSourceGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        JsonRunner("SECRET", returncode=5),
        tmp_path,
        command_resolver=FixedResolver(),
    )

    with pytest.raises(ProductionSourceGeneratorError) as captured:
        generator.generate(_request(tmp_path))

    assert str(captured.value) == (
        "Codex production source command failed with exit code 5"
    )
    assert "SECRET" not in str(captured.value)


def test_should_translate_missing_codex_output_to_safe_error(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    generator = CodexExecProductionSourceGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        JsonRunner(""),
        tmp_path,
        command_resolver=FixedResolver(),
    )

    with pytest.raises(ProductionSourceGeneratorError, match="could not be read"):
        generator.generate(_request(tmp_path))


def test_should_reject_codex_workspace_inside_project_root(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    generator = CodexExecProductionSourceGenerator(
        CommandAnalyzerConfig(("codex",), 12.0, "codex-exec"),
        JsonRunner(""),
        Path("/"),
        command_resolver=FixedResolver(),
    )

    with pytest.raises(ProductionSourceGeneratorError, match="project-external"):
        generator.generate(_request(tmp_path))
