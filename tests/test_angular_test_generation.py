import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.angular_workspace import AngularProject, AngularWorkspace
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.tdd_cycle import select_next_test_case
from sdd_tdd_agent.test_adapter import (
    CASE_SCHEMA,
    JsonCommandTestPlanGenerator,
    TestPlanGeneratorError,
)
from sdd_tdd_agent.test_generation import (
    AngularTestCasePlan,
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    load_test_generation_request,
    run_test_generation,
)


SUBJECT_KINDS = (
    "component",
    "service",
    "directive",
    "pipe",
    "routing",
    "form",
    "http",
)


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
    (session / "design.md").write_text(
        "# Design Proposal\n\n## Overview\n\nUse an Angular service.\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export feature\n\nImplement export.\n",
        encoding="utf-8",
    )
    (session / "test-plan.md").write_text("# Test Plan\n\nPending.\n")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "TEST_GENERATION",
                "current_task": None,
                "current_cycle": 0,
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
                "task_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


def _angular(
    *,
    project: str = "reports",
    subject_kind: str = "component",
    test_facilities: tuple[str, ...] = ("TestBed", "ComponentFixture"),
    template_contracts: tuple[str, ...] = ("Render the export action.",),
) -> AngularTestCasePlan:
    return AngularTestCasePlan(
        project=project,
        subject_kind=subject_kind,
        test_facilities=test_facilities,
        template_contracts=template_contracts,
        dependency_injection=("Provide the export service through TestBed.",),
        async_behavior=("Wait for fixture stability before asserting.",),
    )


def _case(
    *,
    test_file: str = "src/app/export.component.spec.ts",
    angular: Optional[AngularTestCasePlan] = None,
) -> TestCasePlan:
    return TestCasePlan(
        test_id="TC1",
        task_id="T1",
        phase="happy_path",
        title="Export from the component",
        objective="Prove the Angular export interaction.",
        test_file=test_file,
        test_name="exports the current report",
        preconditions=("The report is available.",),
        action="Trigger the export action.",
        expected_outcomes=("The export service receives the report.",),
        dependencies=(),
        angular=_angular() if angular is None else angular,
    )


def _plan(case: Optional[TestCasePlan] = None) -> GeneratedTestPlan:
    return GeneratedTestPlan(
        summary="Verify the Angular export incrementally.",
        cases=(_case() if case is None else case,),
        risks=(),
        open_questions=(),
    )


class RecordingGenerator:
    def __init__(self, plan: GeneratedTestPlan) -> None:
        self.plan = plan
        self.request: Optional[TestGenerationRequest] = None

    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        self.request = request
        return self.plan


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


def _case_payload(case: TestCasePlan) -> dict[str, object]:
    angular = case.angular
    assert angular is not None
    return {
        "test_id": case.test_id,
        "task_id": case.task_id,
        "phase": case.phase,
        "title": case.title,
        "objective": case.objective,
        "test_file": case.test_file,
        "test_name": case.test_name,
        "preconditions": list(case.preconditions),
        "action": case.action,
        "expected_outcomes": list(case.expected_outcomes),
        "dependencies": list(case.dependencies),
        "angular": {
            "project": angular.project,
            "subject_kind": angular.subject_kind,
            "test_facilities": list(angular.test_facilities),
            "template_contracts": list(angular.template_contracts),
            "dependency_injection": list(angular.dependency_injection),
            "async_behavior": list(angular.async_behavior),
        },
    }


def _plan_payload(plan: GeneratedTestPlan) -> dict[str, object]:
    return {
        "summary": plan.summary,
        "cases": [_case_payload(case) for case in plan.cases],
        "risks": list(plan.risks),
        "open_questions": list(plan.open_questions),
    }


def test_should_load_angular_test_context_and_prompt(tmp_path: Path) -> None:
    _workspace(tmp_path)

    request = load_test_generation_request(tmp_path, "feature-1")

    assert request.prompt_version == "v2-angular"
    assert "Angular Test Generation Prompt" in request.prompt
    assert request.angular_context == AngularWorkspace(
        version=1,
        projects=(AngularProject("reports", "application", "", "src", "app"),),
    )


def test_should_render_and_parse_angular_case_without_information_loss(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    plan = _plan()

    run_test_generation(tmp_path, "feature-1", RecordingGenerator(plan))

    rendered = (session / "test-plan.md").read_text(encoding="utf-8")
    assert "Prompt version: `v2-angular`" in rendered
    assert "### Angular project\n\n`reports`" in rendered
    assert "### Angular subject\n\n`component`" in rendered
    assert "### Angular test facilities\n\n- TestBed" in rendered
    assert "### Angular template contracts" in rendered
    assert "### Angular dependency injection" in rendered
    assert "### Angular async behavior" in rendered
    assert select_next_test_case(tmp_path, "feature-1") == plan.cases[0]


@pytest.mark.parametrize("subject_kind", SUBJECT_KINDS)
def test_should_support_each_angular_subject_kind(
    tmp_path: Path,
    subject_kind: str,
) -> None:
    _workspace(tmp_path)
    case = _case(angular=_angular(subject_kind=subject_kind))

    run = run_test_generation(
        tmp_path,
        "feature-1",
        RecordingGenerator(_plan(case)),
    )

    assert run.next_state == "IMPLEMENTATION"


def test_should_require_angular_metadata_before_mutation(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    case = replace(_case(), angular=None)
    original_plan = (session / "test-plan.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Angular test metadata"):
        run_test_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_plan(case)),
        )

    assert (session / "test-plan.md").read_text(encoding="utf-8") == original_plan
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize(
    ("case", "message"),
    [
        (_case(angular=_angular(subject_kind="store")), "subject kind"),
        (_case(angular=_angular(project="unknown")), "project"),
        (_case(test_file="tests/export.component.spec.ts"), "source root"),
        (_case(test_file="src/app/export.component.test.ts"), ".spec.ts"),
        (_case(angular=_angular(test_facilities=())), "facilities"),
        (_case(angular=_angular(template_contracts=(" ",))), "non-empty strings"),
    ],
)
def test_should_reject_invalid_angular_test_metadata(
    tmp_path: Path,
    case: TestCasePlan,
    message: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(ValueError, match=message):
        run_test_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_plan(case)),
        )


def test_should_exchange_angular_context_and_case_metadata(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_test_generation_request(tmp_path, "feature-1")
    plan = _plan()
    runner = RecordingRunner(_plan_payload(plan))
    generator = JsonCommandTestPlanGenerator(
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
    assert decoded.cases[0].angular == plan.cases[0].angular


def test_should_expose_strict_optional_angular_case_schema() -> None:
    properties = CASE_SCHEMA["properties"]
    assert isinstance(properties, dict)
    angular = properties["angular"]
    assert isinstance(angular, dict)

    assert angular["required"] == [
        "project",
        "subject_kind",
        "test_facilities",
        "template_contracts",
        "dependency_injection",
        "async_behavior",
    ]
    assert angular["additionalProperties"] is False


def test_should_reject_invalid_angular_adapter_record(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_test_generation_request(tmp_path, "feature-1")
    output = _plan_payload(_plan())
    cases = output["cases"]
    assert isinstance(cases, list)
    first = cases[0]
    assert isinstance(first, dict)
    angular = first["angular"]
    assert isinstance(angular, dict)
    angular["unexpected"] = True

    with pytest.raises(TestPlanGeneratorError, match="keys do not match schema"):
        JsonCommandTestPlanGenerator(
            CommandAnalyzerConfig(("bridge",), 10.0),
            RecordingRunner(output),
        ).generate(request)


def test_should_reject_angular_case_for_non_angular_project(tmp_path: Path) -> None:
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
        run_test_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_plan()),
        )
