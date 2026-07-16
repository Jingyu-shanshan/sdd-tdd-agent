import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent import design_generation as design
from sdd_tdd_agent.design_adapter import JsonCommandDesignGenerator
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult


def _workspace(root: Path) -> Path:
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": "pnpm@10.2.0",
                "scripts": {"test": "vitest"},
                "devDependencies": {"vitest": "4.1.10"},
            }
        ),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ntarget_language: typescript\nbuild_tool: pnpm\n",
        encoding="utf-8",
    )
    (workspace / "architecture.md").write_text("# Architecture\n")
    (workspace / "conventions.md").write_text("# Conventions\n")
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\n## Summary\n\nExport reports.\n"
    )
    (session / "design.md").write_text("# Design\n\nPending.\n")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "state": "DESIGN",
                "requirement_review": {"decision": "approved"},
            }
        )
    )
    return session


def _generic_proposal() -> design.DesignProposal:
    return design.DesignProposal(
        overview="Add an export module.",
        architecture_decisions=("Keep transport outside the module.",),
        components=("Export module.",),
        data_flow=("Input to export result.",),
        interfaces=(),
        error_handling=(),
        security_considerations=(),
        testing_strategy=("Test the public function with Vitest.",),
        risks_and_tradeoffs=(),
        open_questions=(),
    )


def _generic_fields() -> dict[str, object]:
    proposal = _generic_proposal()
    names = (
        "overview",
        "architecture_decisions",
        "components",
        "data_flow",
        "interfaces",
        "error_handling",
        "security_considerations",
        "testing_strategy",
        "risks_and_tradeoffs",
        "open_questions",
    )
    return {name: getattr(proposal, name) for name in names}


def _typed_proposal() -> design.DesignProposal:
    module_type = getattr(design, "TypeScriptModuleDesign")
    api_type = getattr(design, "TypeScriptPublicApiDesign")
    return replace(
        _generic_proposal(),
        typescript_modules=(
            module_type(
                path="src/reports/exporter.ts",
                responsibility="Create report exports.",
                exports=("exportReport",),
            ),
        ),
        public_apis=(
            api_type(
                name="exportReport",
                kind="function",
                signature="exportReport(input: Report): Promise<Export>",
                module="src/reports/exporter.ts",
            ),
        ),
    )


class RecordingGenerator:
    def __init__(self, proposal: design.DesignProposal) -> None:
        self.proposal = proposal
        self.request: Optional[design.DesignGenerationRequest] = None

    def generate(
        self,
        request: design.DesignGenerationRequest,
    ) -> design.DesignProposal:
        self.request = request
        return self.proposal


class RecordingRunner:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.stdin = ""

    def run(
        self,
        command: tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.stdin = stdin
        return ProcessResult(0, json.dumps(self.output), "")


def test_should_load_versioned_typescript_design_context(tmp_path: Path) -> None:
    _workspace(tmp_path)

    request = design.load_design_generation_request(tmp_path, "feature-1")

    context = request.typescript_context
    assert request.prompt_version == "v2-typescript"
    assert "TypeScript Design Generation Prompt" in request.prompt
    assert context is not None
    assert context.package_manager == "pnpm"
    assert context.test_framework == "vitest"
    assert context.is_angular is False
    assert context.config_files == ("tsconfig.json",)


def test_should_preserve_v1_without_typescript_config_marker(tmp_path: Path) -> None:
    _workspace(tmp_path)
    (tmp_path / "tsconfig.json").unlink()

    request = design.load_design_generation_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert request.typescript_context is None


def test_should_render_typed_modules_and_public_apis(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = design.load_design_generation_request(tmp_path, "feature-1")

    rendered = design.render_design_proposal(request, _typed_proposal())

    assert "## TypeScript project context" in rendered
    assert "Package manager: `pnpm`" in rendered
    assert "## TypeScript modules" in rendered
    assert "### `src/reports/exporter.ts`" in rendered
    assert "Responsibility: Create report exports." in rendered
    assert "## Public APIs" in rendered
    assert "Kind: `function`" in rendered
    assert "Signature: `exportReport(input: Report): Promise<Export>`" in rendered


def test_should_reject_generic_proposal_for_typescript_without_mutation(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    generator = RecordingGenerator(_generic_proposal())
    original_design = (session / "design.md").read_text()
    original_state = (session / "state.json").read_text()

    with pytest.raises(ValueError, match="TypeScript modules"):
        design.run_design_generation(tmp_path, "feature-1", generator)

    assert (session / "design.md").read_text() == original_design
    assert (session / "state.json").read_text() == original_state


@pytest.mark.parametrize(
    ("path", "api_module", "message"),
    [
        ("../secrets.ts", "../secrets.ts", "safe src"),
        ("src/exporter.ts", "src/other.ts", "proposed module"),
    ],
)
def test_should_reject_invalid_typescript_structure(
    tmp_path: Path,
    path: str,
    api_module: str,
    message: str,
) -> None:
    _workspace(tmp_path)
    module_type = getattr(design, "TypeScriptModuleDesign")
    api_type = getattr(design, "TypeScriptPublicApiDesign")
    proposal = replace(
        _generic_proposal(),
        typescript_modules=(module_type(path, "Export reports.", ("exportReport",)),),
        public_apis=(
            api_type(
                "exportReport",
                "function",
                "exportReport(): void",
                api_module,
            ),
        ),
    )

    with pytest.raises(ValueError, match=message):
        design.run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(proposal),
        )


def test_should_exchange_optional_typescript_schema_fields(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = design.load_design_generation_request(tmp_path, "feature-1")
    proposal = _typed_proposal()
    output = {
        **_generic_fields(),
        "typescript_modules": [
            module.__dict__ for module in proposal.typescript_modules
        ],
        "public_apis": [api.__dict__ for api in proposal.public_apis],
    }
    runner = RecordingRunner(output)
    generator = JsonCommandDesignGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        runner,
    )

    decoded = generator.generate(request)

    payload = json.loads(runner.stdin)
    assert payload["typescript_context"] == {
        "package_manager": "pnpm",
        "test_framework": "vitest",
        "is_angular": False,
        "config_files": ["tsconfig.json"],
    }
    assert decoded.typescript_modules == proposal.typescript_modules
    assert decoded.public_apis == proposal.public_apis
