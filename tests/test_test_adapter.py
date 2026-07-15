import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.test_adapter import (
    CodexExecTestPlanGenerator,
    JsonCommandTestPlanGenerator,
    TestPlanGeneratorError,
)
from sdd_tdd_agent.test_generation import TestGenerationRequest


def _request() -> TestGenerationRequest:
    return TestGenerationRequest(
        prompt_version="v1",
        prompt="sensitive test prompt",
        requirement="sensitive approved requirement",
        design="sensitive approved design",
        tasks="sensitive approved tasks",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )


def _case_payload(test_id: str = "TC1") -> Dict[str, object]:
    second = test_id == "TC2"
    return {
        "test_id": test_id,
        "task_id": "T2" if second else "T1",
        "phase": "boundary" if second else "happy_path",
        "title": f"Verify {test_id}",
        "objective": f"Prove behavior for {test_id}.",
        "test_file": "tests/test_export.py",
        "test_name": f"test_should_{test_id.lower()}",
        "preconditions": [],
        "action": "Invoke the export behavior.",
        "expected_outcomes": ["The result is correct."],
        "dependencies": ["TC1"] if second else [],
    }


def _plan_payload() -> Dict[str, object]:
    return {
        "summary": "Verify export incrementally.",
        "cases": [_case_payload("TC1"), _case_payload("TC2")],
        "risks": ["Rendering may differ."],
        "open_questions": ["Which page size is required?"],
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


def test_should_exchange_typed_test_plan_through_json_command() -> None:
    runner = RecordingRunner(
        ProcessResult(0, json.dumps(_plan_payload()), "SECRET-STDERR")
    )
    generator = JsonCommandTestPlanGenerator(
        CommandAnalyzerConfig(("model-bridge", "tests"), 45.0),
        runner,
    )

    plan = generator.generate(_request())

    assert runner.command == ("model-bridge", "tests")
    assert runner.timeout_seconds == 45.0
    assert runner.stdin is not None
    assert json.loads(runner.stdin) == {
        "prompt_version": "v1",
        "prompt": "sensitive test prompt",
        "requirement": "sensitive approved requirement",
        "design": "sensitive approved design",
        "tasks": "sensitive approved tasks",
        "project_metadata": "name: reports",
        "architecture": "# Architecture",
        "conventions": "# Conventions",
    }
    assert plan.summary == "Verify export incrementally."
    assert plan.cases[1].test_id == "TC2"
    assert plan.cases[1].dependencies == ("TC1",)


def _json_generator(stdout: str, returncode: int = 0) -> JsonCommandTestPlanGenerator:
    return JsonCommandTestPlanGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        RecordingRunner(ProcessResult(returncode, stdout, "SECRET-STDERR")),
    )


def test_should_report_json_test_command_exit_without_leaking_content() -> None:
    generator = _json_generator("SECRET-STDOUT", returncode=19)

    with pytest.raises(TestPlanGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == "Test plan generator command failed with exit code 19"
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "must be a JSON object"),
        ("{}", "keys do not match schema"),
        (json.dumps({**_plan_payload(), "summary": 42}), "invalid type: summary"),
        (json.dumps({**_plan_payload(), "cases": "TC1"}), "invalid type: cases"),
        (
            json.dumps({**_plan_payload(), "cases": ["TC1"]}),
            "case 0 must be a JSON object",
        ),
        (
            json.dumps({**_plan_payload(), "cases": [{}]}),
            "case 0 keys do not match schema",
        ),
        (
            json.dumps(
                {
                    **_plan_payload(),
                    "cases": [{**_case_payload(), "unexpected": "value"}],
                }
            ),
            "case 0 keys do not match schema",
        ),
        (
            json.dumps(
                {
                    **_plan_payload(),
                    "cases": [{**_case_payload(), "test_id": 1}],
                }
            ),
            "case 0 field has invalid type: test_id",
        ),
        (
            json.dumps(
                {
                    **_plan_payload(),
                    "cases": [{**_case_payload(), "preconditions": "ready"}],
                }
            ),
            "case 0 field has invalid type: preconditions",
        ),
        (
            json.dumps(
                {
                    **_plan_payload(),
                    "cases": [{**_case_payload(), "dependencies": [1]}],
                }
            ),
            "case 0 field has invalid type: dependencies",
        ),
        (
            json.dumps({**_plan_payload(), "risks": "risk"}),
            "invalid type: risks",
        ),
        (
            json.dumps({**_plan_payload(), "open_questions": [1]}),
            "invalid type: open_questions",
        ),
    ],
)
def test_should_reject_invalid_json_test_plan_response(
    stdout: str,
    message: str,
) -> None:
    with pytest.raises(TestPlanGeneratorError, match=message):
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
            output_path.write_text(json.dumps(_plan_payload()), encoding="utf-8")
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


def test_should_exchange_test_plan_through_read_only_codex_exec(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(0, "progress", ""))
    generator = CodexExecTestPlanGenerator(
        CommandAnalyzerConfig(("codex",), 120.0),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    plan = generator.generate(_request())

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
    assert json.loads(runner.stdin)["tasks"] == "sensitive approved tasks"
    assert isinstance(runner.schema, dict)
    assert runner.schema["required"] == list(_plan_payload())
    assert runner.schema["additionalProperties"] is False
    properties = runner.schema["properties"]
    assert isinstance(properties, dict)
    cases_schema = properties["cases"]
    assert isinstance(cases_schema, dict)
    case_schema = cases_schema["items"]
    assert isinstance(case_schema, dict)
    assert case_schema["required"] == list(_case_payload())
    assert case_schema["additionalProperties"] is False
    assert plan.cases[1].dependencies == ("TC1",)
    assert runner.exchange_directory is not None
    assert not runner.exchange_directory.exists()


def test_should_reject_codex_test_command_with_extra_tokens(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecTestPlanGenerator(
            CommandAnalyzerConfig(("codex", "--unexpected"), 10.0),
            RecordingRunner(ProcessResult(0, "", "")),
            tmp_path,
        )


def test_should_report_codex_test_exit_without_leaking_content(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(23, "SECRET-STDOUT", "SECRET-STDERR"))
    generator = CodexExecTestPlanGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        runner,
        tmp_path,
    )

    with pytest.raises(TestPlanGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == "Codex test plan command failed with exit code 23"
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


def test_should_reject_missing_codex_test_output(tmp_path: Path) -> None:
    generator = CodexExecTestPlanGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        MissingOutputRunner(),
        tmp_path,
    )

    with pytest.raises(TestPlanGeneratorError, match="output could not be read"):
        generator.generate(_request())
