import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.task_adapter import (
    CodexExecTaskBreakdownGenerator,
    JsonCommandTaskBreakdownGenerator,
    TaskBreakdownGeneratorError,
)
from sdd_tdd_agent.task_breakdown import TaskBreakdownRequest


def _request() -> TaskBreakdownRequest:
    return TaskBreakdownRequest(
        prompt_version="v1",
        prompt="sensitive task prompt",
        requirement="sensitive approved requirement",
        design="sensitive approved design",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )


def _task_payload(task_id: str = "T1") -> Dict[str, object]:
    dependencies = [] if task_id == "T1" else ["T1"]
    return {
        "task_id": task_id,
        "title": f"Implement {task_id}",
        "objective": f"Deliver {task_id} safely.",
        "affected_areas": ["sdd_tdd_agent/export.py"],
        "dependencies": dependencies,
        "acceptance_criteria": [f"{task_id} behavior is covered."],
        "test_targets": [f"tests/test_{task_id.lower()}.py"],
    }


def _breakdown_payload() -> Dict[str, object]:
    return {
        "summary": "Deliver export in two ordered tasks.",
        "tasks": [_task_payload("T1"), _task_payload("T2")],
        "global_risks": ["Rendering dependencies may vary."],
        "open_questions": ["Which page sizes are required?"],
    }


class RecordingRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None
        self.timeout_seconds: Optional[float] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        self.timeout_seconds = timeout_seconds
        return self.result


def test_should_exchange_typed_task_breakdown_through_json_command() -> None:
    runner = RecordingRunner(
        ProcessResult(0, json.dumps(_breakdown_payload()), "SECRET-STDERR")
    )
    generator = JsonCommandTaskBreakdownGenerator(
        CommandAnalyzerConfig(("model-bridge", "tasks"), 45.0),
        runner,
    )

    breakdown = generator.generate(_request())

    assert runner.command == ("model-bridge", "tasks")
    assert runner.timeout_seconds == 45.0
    assert runner.stdin is not None
    assert json.loads(runner.stdin) == {
        "prompt_version": "v1",
        "prompt": "sensitive task prompt",
        "requirement": "sensitive approved requirement",
        "design": "sensitive approved design",
        "project_metadata": "name: reports",
        "architecture": "# Architecture",
        "conventions": "# Conventions",
    }
    assert breakdown.summary == "Deliver export in two ordered tasks."
    assert breakdown.tasks[1].task_id == "T2"
    assert breakdown.tasks[1].dependencies == ("T1",)


def _json_generator(
    stdout: str,
    returncode: int = 0,
) -> JsonCommandTaskBreakdownGenerator:
    return JsonCommandTaskBreakdownGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        RecordingRunner(ProcessResult(returncode, stdout, "SECRET-STDERR")),
    )


def test_should_report_json_command_exit_without_leaking_content() -> None:
    generator = _json_generator("SECRET-STDOUT", returncode=19)

    with pytest.raises(TaskBreakdownGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == (
        "Task breakdown generator command failed with exit code 19"
    )
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "must be a JSON object"),
        ("{}", "keys do not match schema"),
        (
            json.dumps({**_breakdown_payload(), "summary": 42}),
            "invalid type: summary",
        ),
        (
            json.dumps({**_breakdown_payload(), "tasks": "T1"}),
            "invalid type: tasks",
        ),
        (
            json.dumps({**_breakdown_payload(), "tasks": ["T1"]}),
            "task 0 must be a JSON object",
        ),
        (
            json.dumps({**_breakdown_payload(), "tasks": [{}]}),
            "task 0 keys do not match schema",
        ),
        (
            json.dumps(
                {
                    **_breakdown_payload(),
                    "tasks": [{**_task_payload(), "unexpected": "value"}],
                }
            ),
            "task 0 keys do not match schema",
        ),
        (
            json.dumps(
                {
                    **_breakdown_payload(),
                    "tasks": [{**_task_payload(), "task_id": 1}],
                }
            ),
            "task 0 field has invalid type: task_id",
        ),
        (
            json.dumps(
                {
                    **_breakdown_payload(),
                    "tasks": [{**_task_payload(), "affected_areas": "file.py"}],
                }
            ),
            "task 0 field has invalid type: affected_areas",
        ),
        (
            json.dumps(
                {
                    **_breakdown_payload(),
                    "tasks": [{**_task_payload(), "dependencies": [1]}],
                }
            ),
            "task 0 field has invalid type: dependencies",
        ),
        (
            json.dumps({**_breakdown_payload(), "global_risks": "risk"}),
            "invalid type: global_risks",
        ),
        (
            json.dumps({**_breakdown_payload(), "open_questions": [1]}),
            "invalid type: open_questions",
        ),
    ],
)
def test_should_reject_invalid_json_task_breakdown_response(
    stdout: str,
    message: str,
) -> None:
    with pytest.raises(TaskBreakdownGeneratorError, match=message):
        _json_generator(stdout).generate(_request())


class RecordingCodexRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None
        self.schema: Optional[object] = None
        self.exchange_directory: Optional[Path] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        self.exchange_directory = schema_path.parent
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if self.result.returncode == 0:
            output_path.write_text(
                json.dumps(_breakdown_payload()),
                encoding="utf-8",
            )
        return self.result


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "/Applications/ChatGPT.app/Contents/Resources/codex"


class MissingOutputRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(0, "", "")


def test_should_exchange_task_breakdown_through_read_only_codex_exec(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(0, "progress", ""))
    generator = CodexExecTaskBreakdownGenerator(
        CommandAnalyzerConfig(("codex",), 120.0),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    breakdown = generator.generate(_request())

    assert runner.command is not None
    assert runner.command[0:2] == (
        "/Applications/ChatGPT.app/Contents/Resources/codex",
        "exec",
    )
    assert "--ephemeral" in runner.command
    assert runner.command[runner.command.index("--sandbox") + 1] == "read-only"
    assert runner.command[runner.command.index("--color") + 1] == "never"
    assert runner.command[runner.command.index("--cd") + 1] == str(tmp_path)
    assert runner.command[-1] == "-"
    assert runner.stdin is not None
    assert json.loads(runner.stdin)["design"] == "sensitive approved design"
    assert isinstance(runner.schema, dict)
    assert runner.schema["required"] == list(_breakdown_payload())
    assert runner.schema["additionalProperties"] is False
    properties = runner.schema["properties"]
    assert isinstance(properties, dict)
    tasks_schema = properties["tasks"]
    assert isinstance(tasks_schema, dict)
    task_schema = tasks_schema["items"]
    assert isinstance(task_schema, dict)
    assert task_schema["required"] == list(_task_payload())
    assert task_schema["additionalProperties"] is False
    assert breakdown.tasks[1].dependencies == ("T1",)
    assert runner.exchange_directory is not None
    assert not runner.exchange_directory.exists()


def test_should_reject_codex_task_command_with_extra_tokens(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecTaskBreakdownGenerator(
            CommandAnalyzerConfig(("codex", "--unexpected"), 10.0),
            RecordingRunner(ProcessResult(0, "", "")),
            tmp_path,
        )


def test_should_report_codex_task_exit_without_leaking_content(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(23, "SECRET-STDOUT", "SECRET-STDERR"))
    generator = CodexExecTaskBreakdownGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        runner,
        tmp_path,
    )

    with pytest.raises(TaskBreakdownGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == (
        "Codex task breakdown command failed with exit code 23"
    )
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


def test_should_reject_missing_codex_task_output(tmp_path: Path) -> None:
    generator = CodexExecTaskBreakdownGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        MissingOutputRunner(),
        tmp_path,
    )

    with pytest.raises(TaskBreakdownGeneratorError, match="output could not be read"):
        generator.generate(_request())
