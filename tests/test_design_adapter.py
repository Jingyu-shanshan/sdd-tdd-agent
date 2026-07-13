import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

from sdd_tdd_agent.design_adapter import (
    CodexExecDesignGenerator,
    DesignGeneratorError,
    JsonCommandDesignGenerator,
)
from sdd_tdd_agent.design_generation import DesignGenerationRequest
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig, ProcessResult


def _request() -> DesignGenerationRequest:
    return DesignGenerationRequest(
        prompt_version="v1",
        prompt="sensitive design prompt",
        requirement="sensitive approved requirement",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )


def _proposal_payload() -> Dict[str, object]:
    return {
        "overview": "Add an export service.",
        "architecture_decisions": ["Keep export outside CLI dispatch."],
        "components": ["Export service."],
        "data_flow": ["Input to service to file."],
        "interfaces": ["PdfExporter.export"],
        "error_handling": ["Reject unsupported input."],
        "security_considerations": ["Redact diagnostics."],
        "testing_strategy": ["Inject and test the writer."],
        "risks_and_tradeoffs": ["Layout is not yet specified."],
        "open_questions": ["Which artifacts are supported?"],
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


def test_should_exchange_typed_design_through_json_command() -> None:
    runner = RecordingRunner(
        ProcessResult(0, json.dumps(_proposal_payload()), "SECRET-STDERR")
    )
    generator = JsonCommandDesignGenerator(
        CommandAnalyzerConfig(("model-bridge", "design"), 45.0),
        runner,
    )

    proposal = generator.generate(_request())

    assert runner.command == ("model-bridge", "design")
    assert runner.timeout_seconds == 45.0
    assert runner.stdin is not None
    assert json.loads(runner.stdin) == {
        "prompt_version": "v1",
        "prompt": "sensitive design prompt",
        "requirement": "sensitive approved requirement",
        "project_metadata": "name: reports",
        "architecture": "# Architecture",
        "conventions": "# Conventions",
    }
    assert proposal.overview == "Add an export service."
    assert proposal.components == ("Export service.",)


def _json_generator(stdout: str, returncode: int = 0) -> JsonCommandDesignGenerator:
    return JsonCommandDesignGenerator(
        CommandAnalyzerConfig(("bridge",), 10.0),
        RecordingRunner(ProcessResult(returncode, stdout, "SECRET-STDERR")),
    )


def test_should_report_json_command_exit_without_leaking_content() -> None:
    generator = _json_generator("SECRET-STDOUT", returncode=19)

    with pytest.raises(DesignGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == "Design generator command failed with exit code 19"
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "must be a JSON object"),
        ("{}", "keys do not match schema"),
        (
            json.dumps({**_proposal_payload(), "overview": 42}),
            "invalid type: overview",
        ),
        (
            json.dumps({**_proposal_payload(), "components": "component"}),
            "invalid type: components",
        ),
        (
            json.dumps({**_proposal_payload(), "components": [1]}),
            "invalid type: components",
        ),
    ],
)
def test_should_reject_invalid_json_design_response(
    stdout: str,
    message: str,
) -> None:
    with pytest.raises(DesignGeneratorError, match=message):
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
                json.dumps(_proposal_payload()),
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


def test_should_exchange_design_through_read_only_codex_exec(tmp_path: Path) -> None:
    runner = RecordingCodexRunner(ProcessResult(0, "progress", ""))
    generator = CodexExecDesignGenerator(
        CommandAnalyzerConfig(("codex",), 120.0),
        runner,
        tmp_path,
        command_resolver=FixedResolver(),
    )

    proposal = generator.generate(_request())

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
    assert json.loads(runner.stdin)["requirement"] == ("sensitive approved requirement")
    assert isinstance(runner.schema, dict)
    assert runner.schema["required"] == list(_proposal_payload())
    assert runner.schema["additionalProperties"] is False
    assert proposal.testing_strategy == ("Inject and test the writer.",)
    assert runner.exchange_directory is not None
    assert not runner.exchange_directory.exists()


def test_should_reject_codex_command_with_extra_tokens(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one executable"):
        CodexExecDesignGenerator(
            CommandAnalyzerConfig(("codex", "--unexpected"), 10.0),
            RecordingRunner(ProcessResult(0, "", "")),
            tmp_path,
        )


def test_should_report_codex_exit_without_leaking_content(tmp_path: Path) -> None:
    runner = RecordingCodexRunner(ProcessResult(23, "SECRET-STDOUT", "SECRET-STDERR"))
    generator = CodexExecDesignGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        runner,
        tmp_path,
    )

    with pytest.raises(DesignGeneratorError) as captured:
        generator.generate(_request())

    assert str(captured.value) == "Codex design command failed with exit code 23"
    assert "SECRET" not in str(captured.value)
    assert "sensitive" not in str(captured.value)


def test_should_reject_missing_codex_design_output(tmp_path: Path) -> None:
    generator = CodexExecDesignGenerator(
        CommandAnalyzerConfig(("codex",), 10.0),
        MissingOutputRunner(),
        tmp_path,
    )

    with pytest.raises(DesignGeneratorError, match="output could not be read"):
        generator.generate(_request())
