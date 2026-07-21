import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.angular_workspace import AngularProject, AngularWorkspace
from sdd_tdd_agent.design_adapter import (
    DESIGN_SCHEMA,
    DesignGeneratorError,
    JsonCommandDesignGenerator,
)
from sdd_tdd_agent.design_generation import (
    AngularArchitectureConstraint,
    DesignGenerationRequest,
    DesignProposal,
    TypeScriptModuleDesign,
    TypeScriptPublicApiDesign,
    load_design_generation_request,
    render_design_proposal,
    run_design_generation,
)
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult


MODULE_PATH = "src/app/export.service.ts"


def _workspace(root: Path) -> Path:
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": "npm@11.0.0",
                "scripts": {"test": "ng test"},
                "dependencies": {"@angular/core": "21.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    (root / "angular.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "reports": {
                        "projectType": "application",
                        "root": "",
                        "sourceRoot": "src",
                        "prefix": "app",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    agent = root / ".agent"
    session = agent / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (agent / "project.yml").write_text(
        "name: reports\ntarget_language: typescript\nbuild_tool: npm\n",
        encoding="utf-8",
    )
    (agent / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (agent / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\n## Summary\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text("# Design\n\nPending.\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "state": "DESIGN",
                "requirement_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


def _generic_proposal() -> DesignProposal:
    return DesignProposal(
        overview="Add an Angular export service.",
        architecture_decisions=("Use an injectable service.",),
        components=("Export service.",),
        data_flow=("Component to service to result.",),
        interfaces=(),
        error_handling=(),
        security_considerations=(),
        testing_strategy=("Test through Angular dependency injection.",),
        risks_and_tradeoffs=(),
        open_questions=(),
    )


def _constraint(
    area: str = "dependency-injection",
    decision: str = "Inject the export port into ExportService.",
) -> AngularArchitectureConstraint:
    return AngularArchitectureConstraint(
        area=area,
        decision=decision,
        rationale="Keep infrastructure replaceable in tests.",
        verification="Resolve the service through the Angular test injector.",
    )


def _proposal(
    constraints: tuple[AngularArchitectureConstraint, ...] = (_constraint(),),
) -> DesignProposal:
    return replace(
        _generic_proposal(),
        typescript_modules=(
            TypeScriptModuleDesign(
                MODULE_PATH,
                "Coordinate report exports.",
                ("ExportService",),
            ),
        ),
        public_apis=(
            TypeScriptPublicApiDesign(
                "ExportService",
                "service",
                "exportReport(input: Report): Observable<Export>",
                MODULE_PATH,
            ),
        ),
        angular_constraints=constraints,
    )


class RecordingGenerator:
    def __init__(self, proposal: DesignProposal) -> None:
        self.proposal = proposal
        self.request: Optional[DesignGenerationRequest] = None

    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
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


def _payload(proposal: DesignProposal) -> dict[str, object]:
    return {
        "overview": proposal.overview,
        "architecture_decisions": list(proposal.architecture_decisions),
        "components": list(proposal.components),
        "data_flow": list(proposal.data_flow),
        "interfaces": list(proposal.interfaces),
        "error_handling": list(proposal.error_handling),
        "security_considerations": list(proposal.security_considerations),
        "testing_strategy": list(proposal.testing_strategy),
        "risks_and_tradeoffs": list(proposal.risks_and_tradeoffs),
        "open_questions": list(proposal.open_questions),
        "typescript_modules": [
            {
                "path": module.path,
                "responsibility": module.responsibility,
                "exports": list(module.exports),
            }
            for module in proposal.typescript_modules
        ],
        "public_apis": [api.__dict__ for api in proposal.public_apis],
        "angular_constraints": [
            constraint.__dict__ for constraint in proposal.angular_constraints
        ],
    }


def test_should_load_angular_workspace_context_and_prompt(tmp_path: Path) -> None:
    _workspace(tmp_path)

    request = load_design_generation_request(tmp_path, "feature-1")

    assert request.prompt_version == "v3-angular"
    assert "Angular Design Generation Prompt" in request.prompt
    assert request.angular_context == AngularWorkspace(
        version=1,
        projects=(AngularProject("reports", "application", "", "src", "app"),),
    )


def test_should_render_angular_workspace_and_constraints(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_design_generation_request(tmp_path, "feature-1")

    rendered = render_design_proposal(request, _proposal())

    assert "## Angular workspace" in rendered
    assert "Workspace version: `1`" in rendered
    assert "### `reports`" in rendered
    assert "Project type: `application`" in rendered
    assert "Source root: `src`" in rendered
    assert "## Angular architecture constraints" in rendered
    assert "### `dependency-injection`" in rendered
    assert "Decision: Inject the export port into ExportService." in rendered
    assert "Verification: Resolve the service through the Angular test injector." in (
        rendered
    )


def test_should_allow_module_within_configured_library_source_root(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    (tmp_path / "angular.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "reports-lib": {
                        "projectType": "library",
                        "root": "projects/reports",
                        "sourceRoot": "projects/reports/src",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    module_path = "projects/reports/src/lib/export.service.ts"
    proposal = replace(
        _proposal(),
        typescript_modules=(
            TypeScriptModuleDesign(
                module_path,
                "Coordinate report exports.",
                ("ExportService",),
            ),
        ),
        public_apis=(
            TypeScriptPublicApiDesign(
                "ExportService",
                "service",
                "exportReport(input: Report): Observable<Export>",
                module_path,
            ),
        ),
    )

    run = run_design_generation(
        tmp_path,
        "feature-1",
        RecordingGenerator(proposal),
    )

    assert run.next_state == "DESIGN_REVIEW"


def test_should_reject_module_outside_configured_library_source_root(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    (tmp_path / "angular.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "reports-lib": {
                        "projectType": "library",
                        "root": "projects/reports",
                        "sourceRoot": "projects/reports/src",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Angular source root"):
        run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_proposal()),
        )


def test_should_require_constraints_before_angular_design_mutation(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    original_design = (session / "design.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Angular architecture constraints"):
        run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_proposal(())),
        )

    assert (session / "design.md").read_text(encoding="utf-8") == original_design
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize(
    ("constraints", "message"),
    [
        ((_constraint(area="global-singletons"),), "area is unsupported"),
        ((_constraint(), _constraint(decision="Use a feature provider.")), "unique"),
        ((_constraint(decision=" "),), "fields must not be blank"),
    ],
)
def test_should_reject_invalid_angular_constraints(
    tmp_path: Path,
    constraints: tuple[AngularArchitectureConstraint, ...],
    message: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(ValueError, match=message):
        run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_proposal(constraints)),
        )


def test_should_exchange_angular_context_and_constraints(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_design_generation_request(tmp_path, "feature-1")
    proposal = _proposal()
    runner = RecordingRunner(_payload(proposal))
    generator = JsonCommandDesignGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        runner,
    )

    decoded = generator.generate(request)

    payload = json.loads(runner.stdin)
    assert payload["angular_context"] == {
        "version": 1,
        "projects": [
            {
                "name": "reports",
                "project_type": "application",
                "root": "",
                "source_root": "src",
                "prefix": "app",
            }
        ],
    }
    assert decoded.angular_constraints == proposal.angular_constraints


def test_should_expose_strict_angular_constraint_output_schema() -> None:
    properties = DESIGN_SCHEMA["properties"]
    assert isinstance(properties, dict)
    angular = properties["angular_constraints"]
    assert isinstance(angular, dict)
    items = angular["items"]
    assert isinstance(items, dict)

    assert items["required"] == [
        "area",
        "decision",
        "rationale",
        "verification",
    ]
    assert items["additionalProperties"] is False


def test_should_reject_invalid_angular_constraint_adapter_record(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    request = load_design_generation_request(tmp_path, "feature-1")
    output = _payload(_proposal())
    records = output["angular_constraints"]
    assert isinstance(records, list)
    records[0]["unexpected"] = True

    with pytest.raises(DesignGeneratorError, match="invalid fields"):
        JsonCommandDesignGenerator(
            CommandAnalyzerConfig(("bridge",), 10.0),
            RecordingRunner(output),
        ).generate(request)


def test_should_reject_angular_records_for_non_angular_typescript(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": "npm@11.0.0",
                "scripts": {"test": "vitest"},
                "devDependencies": {"vitest": "4.1.0"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "angular.json").unlink()

    with pytest.raises(ValueError, match="Non-Angular"):
        run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_proposal()),
        )
