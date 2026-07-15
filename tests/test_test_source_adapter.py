import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult
from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.test_generation import TestCasePlan
from sdd_tdd_agent.test_source_adapter import (
    CodexExecTestSourceGenerator,
    JsonCommandTestSourceGenerator,
    TestSourceGeneratorError,
)
from sdd_tdd_agent.test_source_generation import TestSourceGenerationRequest


def _request() -> TestSourceGenerationRequest:
    current = TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export a report",
        "Prove export.",
        "tests/test_export.py",
        "test_should_export_report",
        ("A report exists.",),
        "Export it.",
        ("A PDF is returned.",),
        (),
    )
    return TestSourceGenerationRequest(
        prompt_version="v1",
        prompt="SENSITIVE TEST PROMPT",
        requirement="SENSITIVE REQUIREMENT",
        design="SENSITIVE DESIGN",
        current_test=current,
        sources=(SourceSnapshot("src/export.py", "SENSITIVE SOURCE"),),
    )


def _response() -> Dict[str, str]:
    return {
        "test_id": "TC1",
        "file_path": "tests/test_export.py",
        "content": "def test_should_export_report():\n    assert False\n",
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


def test_should_exchange_one_test_source_through_json_command() -> None:
    runner = RecordingRunner(ProcessResult(0, json.dumps(_response()), "SECRET"))
    generator = JsonCommandTestSourceGenerator(
        CommandAnalyzerConfig(("bridge", "test-source"), 45.0),
        runner,
    )

    generated = generator.generate(_request())

    assert runner.command == ("bridge", "test-source")
    assert runner.timeout_seconds == 45.0
    assert runner.stdin is not None
    payload = json.loads(runner.stdin)
    assert set(payload) == {
        "prompt_version",
        "prompt",
        "requirement",
        "design",
        "current_test",
        "sources",
    }
    assert payload["current_test"] == {
        "test_id": "TC1",
        "task_id": "T1",
        "phase": "happy_path",
        "title": "Export a report",
        "objective": "Prove export.",
        "test_file": "tests/test_export.py",
        "test_name": "test_should_export_report",
        "preconditions": ["A report exists."],
        "action": "Export it.",
        "expected_outcomes": ["A PDF is returned."],
        "dependencies": [],
    }
    assert payload["sources"] == [
        {"path": "src/export.py", "content": "SENSITIVE SOURCE"}
    ]
    assert generated.test_id == "TC1"
    assert generated.file_path == "tests/test_export.py"


def _json_generator(
    stdout: str,
    returncode: int = 0,
) -> JsonCommandTestSourceGenerator:
    return JsonCommandTestSourceGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        RecordingRunner(ProcessResult(returncode, stdout, "SECRET-STDERR")),
    )


def test_should_report_test_source_command_failure_without_sensitive_content() -> None:
    generator = _json_generator("SECRET-STDOUT", returncode=23)

    with pytest.raises(TestSourceGeneratorError) as captured:
        generator.generate(_request())

    message = str(captured.value)
    assert message == "Test source generator command failed with exit code 23"
    assert "SECRET" not in message
    assert "SENSITIVE" not in message


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "must be a JSON object"),
        ("{}", "keys do not match schema"),
        (json.dumps({**_response(), "extra": "value"}), "keys do not match schema"),
        (json.dumps({**_response(), "test_id": 1}), "invalid type: test_id"),
        (json.dumps({**_response(), "file_path": []}), "invalid type: file_path"),
        (json.dumps({**_response(), "content": None}), "invalid type: content"),
        (json.dumps({**_response(), "test_id": "TC2"}), "test identifier"),
        (json.dumps({**_response(), "file_path": "tests/other.py"}), "file path"),
    ],
)
def test_should_reject_invalid_test_source_response(
    stdout: str,
    message: str,
) -> None:
    with pytest.raises((TestSourceGeneratorError, ValueError), match=message):
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
            output_path.write_text(json.dumps(_response()), encoding="utf-8")
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


def test_should_exchange_test_source_through_read_only_codex_exec(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(0, "progress", ""))
    generator = CodexExecTestSourceGenerator(
        CommandAnalyzerConfig(("codex",), 120.0),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    generated = generator.generate(_request())

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
    assert json.loads(runner.stdin)["current_test"]["test_id"] == "TC1"
    assert isinstance(runner.schema, dict)
    assert runner.schema["required"] == ["test_id", "file_path", "content"]
    assert runner.schema["additionalProperties"] is False
    assert generated.content.startswith("def test_should_export_report")
    assert runner.exchange_directory is not None
    assert not runner.exchange_directory.exists()


def test_should_reject_invalid_codex_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecTestSourceGenerator(
            CommandAnalyzerConfig(("codex", "extra"), 10.0),
            RecordingRunner(ProcessResult(0, "", "")),
            tmp_path,
        )


def test_should_report_missing_codex_output_without_paths(tmp_path: Path) -> None:
    generator = CodexExecTestSourceGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        MissingOutputRunner(),
        tmp_path,
        command_resolver=FixedResolver(),
    )

    with pytest.raises(TestSourceGeneratorError) as captured:
        generator.generate(_request())

    message = str(captured.value)
    assert message == "Codex test source output could not be read"
    assert "/tmp" not in message
    assert "SENSITIVE" not in message


def test_should_report_codex_failure_without_sensitive_content(
    tmp_path: Path,
) -> None:
    runner = RecordingCodexRunner(ProcessResult(17, "SECRET", "SECRET"))
    generator = CodexExecTestSourceGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    with pytest.raises(TestSourceGeneratorError) as captured:
        generator.generate(_request())

    message = str(captured.value)
    assert message == "Codex test source command failed with exit code 17"
    assert "SECRET" not in message
    assert "SENSITIVE" not in message
