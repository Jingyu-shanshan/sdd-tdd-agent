import hashlib
import json
from pathlib import Path

import pytest

from sdd_tdd_agent.production_source_adapter import (
    JsonCommandProductionSourceGenerator,
)
from sdd_tdd_agent.production_source_command import (
    generate_active_production_source,
)
from sdd_tdd_agent.production_source_generation import (
    GeneratedProductionSource,
    load_production_source_generation_request,
    validate_generated_production_source,
)
from sdd_tdd_agent.production_source_workspace import (
    AtomicProductionSourceWriter,
    WorkspaceProductionSourceCollector,
)
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.green_verification import (
    GreenVerificationError,
    validate_production_source_artifact,
    verify_active_implementation,
)
from sdd_tdd_agent.cycle_completion import complete_active_implementation
from sdd_tdd_agent.implementation_review import run_active_implementation_review
from sdd_tdd_agent.refactor_completion import complete_active_refactor
from sdd_tdd_agent.red_execution import TestCommandProcessResult
from sdd_tdd_agent.test_generation import (
    AngularTestCasePlan,
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from tests.production_source_support import create_red_workspace


SOURCE_ROOT = "projects/shared/src"
TEST_PATH = f"{SOURCE_ROOT}/lib/export.service.spec.ts"
SOURCE_PATH = f"{SOURCE_ROOT}/lib/export.service.ts"
SOURCE_CONTENT = "export class ExportService {}\n"


def _angular_case() -> TestCasePlan:
    return TestCasePlan(
        test_id="TC1",
        task_id="T1",
        phase="happy_path",
        title="Export a report",
        objective="Return the report.",
        test_file=TEST_PATH,
        test_name="exports report",
        preconditions=(),
        action="Call the export service.",
        expected_outcomes=("The report is returned.",),
        dependencies=(),
        angular=AngularTestCasePlan(
            project="shared",
            subject_kind="service",
            test_facilities=("TestBed",),
            template_contracts=(),
            dependency_injection=("Inject ExportService.",),
            async_behavior=(),
        ),
    )


def _workspace(root: Path) -> Path:
    session = create_red_workspace(root)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "workspace",
                "packageManager": "npm@11.0.0",
                "scripts": {"test": "ng test"},
                "dependencies": {"@angular/core": "21.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (root / "angular.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "app": {
                        "projectType": "application",
                        "root": "projects/app",
                        "sourceRoot": "projects/app/src",
                    },
                    "shared": {
                        "projectType": "library",
                        "root": "projects/shared",
                        "sourceRoot": SOURCE_ROOT,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    source = root / SOURCE_PATH
    source.parent.mkdir(parents=True)
    source.write_text(SOURCE_CONTENT, encoding="utf-8")
    test = root / TEST_PATH
    test.write_text("describe('ExportService', () => {});\n", encoding="utf-8")
    request = TestGenerationRequest("v2-angular", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan("Angular library case.", (_angular_case(),), (), ())
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    (session / "review.md").write_text(
        "# Review\n\nPending requirement analysis.\n",
        encoding="utf-8",
    )
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["test_source"] = {
        "test_id": "TC1",
        "file_path": TEST_PATH,
        "sha256": hashlib.sha256(test.read_bytes()).hexdigest(),
    }
    state["red_evidence"]["file_path"] = TEST_PATH
    state["red_evidence"]["stdout"] = f"{TEST_PATH}: exports report failed\n"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return session


def _request(root: Path):
    sources = WorkspaceProductionSourceCollector().collect(root, (SOURCE_ROOT,))
    return load_production_source_generation_request(
        root,
        "feature-1",
        sources,
        (SOURCE_ROOT,),
    )


class RecordingRunner:
    def __init__(self, file_path: str = SOURCE_PATH) -> None:
        self.file_path = file_path
        self.stdin = ""

    def run(
        self,
        command: tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.stdin = stdin
        return ProcessResult(
            0,
            json.dumps(
                {
                    "test_id": "TC1",
                    "file_path": self.file_path,
                    "content": "export class ExportService { export(): string { return 'ok'; } }\n",
                }
            ),
            "",
        )


class PassingTestRunner:
    def run(
        self,
        command: tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        return TestCommandProcessResult(0, "passed\n", "")


def test_should_load_only_current_angular_project_production_root(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)

    request = _request(tmp_path)

    assert request.prompt_version == "v2-angular"
    assert request.production_source_roots == (SOURCE_ROOT,)
    assert tuple(item.path for item in request.context.production_sources) == (
        SOURCE_PATH,
    )
    assert "angular.json" not in request.prompt


def test_should_exchange_exact_angular_production_root(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runner = RecordingRunner()
    generator = JsonCommandProductionSourceGenerator(
        CommandAnalyzerConfig(("provider",), 10.0),
        runner,
    )

    generated = generator.generate(_request(tmp_path))

    payload = json.loads(runner.stdin)
    assert payload["production_source_roots"] == [SOURCE_ROOT]
    assert generated.file_path == SOURCE_PATH
    serialized = runner.stdin
    assert "angular.json" not in serialized
    assert "DESIGN-SENTINEL" not in serialized


def test_should_write_inside_angular_library_source_root(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = _request(tmp_path)
    generated = GeneratedProductionSource(
        "TC1",
        SOURCE_PATH,
        "export class ExportService { export(): string { return 'ok'; } }\n",
    )

    result = AtomicProductionSourceWriter().write(tmp_path, request, generated)

    assert result.replaced_existing is True
    assert (tmp_path / SOURCE_PATH).read_text(encoding="utf-8") == generated.content


def test_should_not_collect_through_symlinked_angular_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    source = outside / "shared" / "src" / "lib" / "export.service.ts"
    source.parent.mkdir(parents=True)
    source.write_text(SOURCE_CONTENT, encoding="utf-8")
    (project / "projects").symlink_to(outside)

    snapshots = WorkspaceProductionSourceCollector().collect(
        project,
        (SOURCE_ROOT,),
    )

    assert snapshots == ()


def test_should_reject_sibling_angular_project_source(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = _request(tmp_path)

    with pytest.raises(ValueError, match="production source path"):
        validate_generated_production_source(
            request,
            GeneratedProductionSource(
                "TC1",
                "projects/app/src/app/export.component.ts",
                "export class ExportComponent {}\n",
            ),
        )


def test_should_bind_angular_source_root_through_green_audit(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)

    run = generate_active_production_source(tmp_path, RecordingRunner())
    artifact = validate_production_source_artifact(
        tmp_path,
        "feature-1",
        "IMPLEMENT",
    )

    assert run.file_path == SOURCE_PATH
    assert artifact.source_root == SOURCE_ROOT
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["production_source"]["source_root"] == SOURCE_ROOT


def test_should_reject_tampered_angular_source_root_during_green_audit(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    generate_active_production_source(tmp_path, RecordingRunner())
    state_path = session / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["production_source"]["source_root"] = "projects"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(GreenVerificationError, match="Production source record"):
        validate_production_source_artifact(
            tmp_path,
            "feature-1",
            "IMPLEMENT",
        )


def test_should_preserve_angular_root_through_done_audit_chain(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    runner = PassingTestRunner()
    generate_active_production_source(tmp_path, RecordingRunner())

    verify_active_implementation(tmp_path, runner)
    complete_active_implementation(tmp_path)
    run_active_implementation_review(tmp_path)
    complete_active_refactor(tmp_path, runner)

    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DONE"
    assert state["production_source"]["source_root"] == SOURCE_ROOT
