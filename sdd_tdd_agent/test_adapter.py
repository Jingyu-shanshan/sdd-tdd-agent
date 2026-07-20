import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, cast

from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    RequirementAnalyzerError,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.test_generation import (
    AngularTestCasePlan,
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
)


CASE_FIELDS = (
    "test_id",
    "task_id",
    "phase",
    "title",
    "objective",
    "test_file",
    "test_name",
    "preconditions",
    "action",
    "expected_outcomes",
    "dependencies",
)
OPTIONAL_CASE_FIELDS = ("angular",)
ANGULAR_CASE_FIELDS = (
    "project",
    "subject_kind",
    "test_facilities",
    "template_contracts",
    "dependency_injection",
    "async_behavior",
)
PLAN_FIELDS = (
    "summary",
    "cases",
    "risks",
    "open_questions",
)
STRING_CASE_FIELDS = (
    "test_id",
    "task_id",
    "phase",
    "title",
    "objective",
    "test_file",
    "test_name",
    "action",
)

CASE_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "test_id": {"type": "string"},
        "task_id": {"type": "string"},
        "phase": {"type": "string"},
        "title": {"type": "string"},
        "objective": {"type": "string"},
        "test_file": {"type": "string"},
        "test_name": {"type": "string"},
        "preconditions": {"type": "array", "items": {"type": "string"}},
        "action": {"type": "string"},
        "expected_outcomes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "angular": {
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "subject_kind": {"type": "string"},
                "test_facilities": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "template_contracts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "dependency_injection": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "async_behavior": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": list(ANGULAR_CASE_FIELDS),
            "additionalProperties": False,
        },
    },
    "required": list(CASE_FIELDS),
    "additionalProperties": False,
}

TEST_PLAN_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "cases": {"type": "array", "items": CASE_SCHEMA},
        "risks": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(PLAN_FIELDS),
    "additionalProperties": False,
}


class TestPlanGeneratorError(RequirementAnalyzerError):
    """Safe public error raised by a test-plan generator adapter."""

    __test__ = False


def _request_payload(request: TestGenerationRequest) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "requirement": request.requirement,
        "design": request.design,
        "tasks": request.tasks,
        "project_metadata": request.project_metadata,
        "architecture": request.architecture,
        "conventions": request.conventions,
    }
    angular = request.angular_context
    if angular is not None:
        payload["angular_context"] = {
            "version": angular.version,
            "projects": [
                {
                    "name": project.name,
                    "project_type": project.project_type,
                    "root": project.root,
                    "source_root": project.source_root,
                    "prefix": project.prefix,
                }
                for project in angular.projects
            ],
        }
    return payload


def _string_tuple(
    payload: Dict[str, object],
    key: str,
    subject: str,
) -> Tuple[str, ...]:
    value = payload[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TestPlanGeneratorError(f"{subject} field has invalid type: {key}")
    return tuple(value)


def _decode_angular_case(value: object, subject: str) -> AngularTestCasePlan:
    if not isinstance(value, dict) or set(value) != set(ANGULAR_CASE_FIELDS):
        raise TestPlanGeneratorError(f"{subject} Angular keys do not match schema")
    payload: Dict[str, object] = value
    project = payload["project"]
    subject_kind = payload["subject_kind"]
    if not isinstance(project, str) or not isinstance(subject_kind, str):
        raise TestPlanGeneratorError(f"{subject} Angular field has invalid type")
    return AngularTestCasePlan(
        project=project,
        subject_kind=subject_kind,
        test_facilities=_string_tuple(payload, "test_facilities", subject),
        template_contracts=_string_tuple(payload, "template_contracts", subject),
        dependency_injection=_string_tuple(
            payload,
            "dependency_injection",
            subject,
        ),
        async_behavior=_string_tuple(payload, "async_behavior", subject),
    )


def _decode_case(value: object, index: int) -> TestCasePlan:
    subject = f"Test plan generator case {index}"
    if not isinstance(value, dict):
        raise TestPlanGeneratorError(f"{subject} must be a JSON object")
    payload: Dict[str, object] = value
    fields = set(payload)
    allowed = set(CASE_FIELDS) | set(OPTIONAL_CASE_FIELDS)
    if not set(CASE_FIELDS).issubset(fields) or not fields.issubset(allowed):
        raise TestPlanGeneratorError(f"{subject} keys do not match schema")
    for key in STRING_CASE_FIELDS:
        if not isinstance(payload[key], str):
            raise TestPlanGeneratorError(f"{subject} field has invalid type: {key}")
    return TestCasePlan(
        test_id=cast(str, payload["test_id"]),
        task_id=cast(str, payload["task_id"]),
        phase=cast(str, payload["phase"]),
        title=cast(str, payload["title"]),
        objective=cast(str, payload["objective"]),
        test_file=cast(str, payload["test_file"]),
        test_name=cast(str, payload["test_name"]),
        preconditions=_string_tuple(payload, "preconditions", subject),
        action=cast(str, payload["action"]),
        expected_outcomes=_string_tuple(payload, "expected_outcomes", subject),
        dependencies=_string_tuple(payload, "dependencies", subject),
        angular=(
            _decode_angular_case(payload["angular"], subject)
            if "angular" in payload
            else None
        ),
    )


def _decode_plan(content: str) -> GeneratedTestPlan:
    try:
        payload_value = json.loads(content)
    except json.JSONDecodeError as error:
        raise TestPlanGeneratorError(
            "Test plan generator returned invalid JSON"
        ) from error
    if not isinstance(payload_value, dict):
        raise TestPlanGeneratorError(
            "Test plan generator response must be a JSON object"
        )
    payload: Dict[str, object] = payload_value
    if set(payload) != set(PLAN_FIELDS):
        raise TestPlanGeneratorError(
            "Test plan generator response keys do not match schema"
        )
    summary = payload["summary"]
    cases = payload["cases"]
    if not isinstance(summary, str):
        raise TestPlanGeneratorError(
            "Test plan generator field has invalid type: summary"
        )
    if not isinstance(cases, list):
        raise TestPlanGeneratorError(
            "Test plan generator field has invalid type: cases"
        )
    return GeneratedTestPlan(
        summary=summary,
        cases=tuple(_decode_case(case, index) for index, case in enumerate(cases)),
        risks=_string_tuple(payload, "risks", "Test plan generator"),
        open_questions=_string_tuple(
            payload,
            "open_questions",
            "Test plan generator",
        ),
    )


class JsonCommandTestPlanGenerator:
    """Test-plan generator using the strict provider-neutral JSON protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        """Exchange one typed test-plan request through the configured runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise TestPlanGeneratorError(
                f"Test plan generator command failed with exit code {result.returncode}"
            )
        return _decode_plan(result.stdout)


class CodexExecTestPlanGenerator:
    """Test-plan generator backed by an ephemeral read-only Codex CLI run."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex test command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        """Exchange one test-plan request through structured Codex exec."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(prefix="sdd-tdd-codex-test-plan-") as path:
                exchange = Path(path)
                schema_path = exchange / "test-plan.schema.json"
                output_path = exchange / "test-plan.json"
                schema_path.write_text(
                    json.dumps(TEST_PLAN_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise TestPlanGeneratorError(
                        "Codex test plan command failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_plan(output_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TestPlanGeneratorError(
                "Codex test plan output could not be read"
            ) from error

    def _command(self, schema_path: Path, output_path: Path) -> Tuple[str, ...]:
        return (self._executable,) + (
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "--cd",
            str(self._workspace),
            "-",
        )
