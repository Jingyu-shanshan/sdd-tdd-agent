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
from sdd_tdd_agent.task_breakdown import (
    DevelopmentTask,
    TaskBreakdown,
    TaskBreakdownRequest,
)


TASK_FIELDS = (
    "task_id",
    "title",
    "objective",
    "affected_areas",
    "dependencies",
    "acceptance_criteria",
    "test_targets",
)
TASK_BREAKDOWN_FIELDS = (
    "summary",
    "tasks",
    "global_risks",
    "open_questions",
)

TASK_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"},
        "title": {"type": "string"},
        "objective": {"type": "string"},
        "affected_areas": {"type": "array", "items": {"type": "string"}},
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "acceptance_criteria": {
            "type": "array",
            "items": {"type": "string"},
        },
        "test_targets": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(TASK_FIELDS),
    "additionalProperties": False,
}

TASK_BREAKDOWN_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": TASK_SCHEMA,
        },
        "global_risks": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(TASK_BREAKDOWN_FIELDS),
    "additionalProperties": False,
}


class TaskBreakdownGeneratorError(RequirementAnalyzerError):
    """Safe public error raised by a task-breakdown generator adapter."""


def _request_payload(request: TaskBreakdownRequest) -> Dict[str, str]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "requirement": request.requirement,
        "design": request.design,
        "project_metadata": request.project_metadata,
        "architecture": request.architecture,
        "conventions": request.conventions,
    }


def _string_tuple(
    payload: Dict[str, object],
    key: str,
    subject: str,
) -> Tuple[str, ...]:
    value = payload[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TaskBreakdownGeneratorError(f"{subject} field has invalid type: {key}")
    return tuple(value)


def _decode_task(value: object, index: int) -> DevelopmentTask:
    subject = f"Task breakdown generator task {index}"
    if not isinstance(value, dict):
        raise TaskBreakdownGeneratorError(f"{subject} must be a JSON object")
    payload: Dict[str, object] = value
    if set(payload) != set(TASK_FIELDS):
        raise TaskBreakdownGeneratorError(f"{subject} keys do not match schema")
    task_id = payload["task_id"]
    title = payload["title"]
    objective = payload["objective"]
    for key, scalar in (
        ("task_id", task_id),
        ("title", title),
        ("objective", objective),
    ):
        if not isinstance(scalar, str):
            raise TaskBreakdownGeneratorError(
                f"{subject} field has invalid type: {key}"
            )
    return DevelopmentTask(
        task_id=cast(str, task_id),
        title=cast(str, title),
        objective=cast(str, objective),
        affected_areas=_string_tuple(payload, "affected_areas", subject),
        dependencies=_string_tuple(payload, "dependencies", subject),
        acceptance_criteria=_string_tuple(payload, "acceptance_criteria", subject),
        test_targets=_string_tuple(payload, "test_targets", subject),
    )


def _decode_breakdown(content: str) -> TaskBreakdown:
    try:
        payload_value = json.loads(content)
    except json.JSONDecodeError as error:
        raise TaskBreakdownGeneratorError(
            "Task breakdown generator returned invalid JSON"
        ) from error
    if not isinstance(payload_value, dict):
        raise TaskBreakdownGeneratorError(
            "Task breakdown generator response must be a JSON object"
        )
    payload: Dict[str, object] = payload_value
    if set(payload) != set(TASK_BREAKDOWN_FIELDS):
        raise TaskBreakdownGeneratorError(
            "Task breakdown generator response keys do not match schema"
        )
    summary = payload["summary"]
    tasks = payload["tasks"]
    if not isinstance(summary, str):
        raise TaskBreakdownGeneratorError(
            "Task breakdown generator field has invalid type: summary"
        )
    if not isinstance(tasks, list):
        raise TaskBreakdownGeneratorError(
            "Task breakdown generator field has invalid type: tasks"
        )
    return TaskBreakdown(
        summary=summary,
        tasks=tuple(_decode_task(task, index) for index, task in enumerate(tasks)),
        global_risks=_string_tuple(
            payload,
            "global_risks",
            "Task breakdown generator",
        ),
        open_questions=_string_tuple(
            payload,
            "open_questions",
            "Task breakdown generator",
        ),
    )


class JsonCommandTaskBreakdownGenerator:
    """Task generator using the strict provider-neutral JSON protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def generate(self, request: TaskBreakdownRequest) -> TaskBreakdown:
        """Exchange one typed task request through the configured runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise TaskBreakdownGeneratorError(
                "Task breakdown generator command failed with exit code "
                f"{result.returncode}"
            )
        return _decode_breakdown(result.stdout)


class CodexExecTaskBreakdownGenerator:
    """Task generator backed by an ephemeral read-only Codex CLI run."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex task command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def generate(self, request: TaskBreakdownRequest) -> TaskBreakdown:
        """Exchange one task request through a structured Codex exec run."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(prefix="sdd-tdd-codex-tasks-") as path:
                exchange = Path(path)
                schema_path = exchange / "tasks.schema.json"
                output_path = exchange / "tasks.json"
                schema_path.write_text(
                    json.dumps(TASK_BREAKDOWN_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise TaskBreakdownGeneratorError(
                        "Codex task breakdown command failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_breakdown(output_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TaskBreakdownGeneratorError(
                "Codex task breakdown output could not be read"
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
