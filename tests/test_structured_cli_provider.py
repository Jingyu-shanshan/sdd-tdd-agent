import json
from typing import Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
    structured_cli_runner,
)


class RecordingRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[Tuple[str, ...], str, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, stdin, timeout_seconds))
        return self.result


@pytest.mark.parametrize(
    ("protocol", "executable", "expected_command"),
    [
        (
            "claude-exec",
            "claude",
            (
                "claude",
                "-p",
                "--output-format",
                "json",
                "--permission-mode",
                "plan",
                "--no-session-persistence",
            ),
        ),
        (
            "cursor-exec",
            "cursor-agent",
            ("cursor-agent", "-p", "--output-format", "json"),
        ),
    ],
)
def test_should_normalize_verified_cli_result(
    protocol: str,
    executable: str,
    expected_command: Tuple[str, ...],
) -> None:
    provider_output = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": json.dumps({"answer": "ok"}),
            "session_id": "ignored-documented-field",
        }
    )
    delegate = RecordingRunner(ProcessResult(0, provider_output, "ignored"))
    config = CommandAnalyzerConfig((executable,), 41, protocol)
    runner = structured_cli_runner(config, delegate)

    result = runner.run(config.command, '{"request":"typed"}', 41)

    assert delegate.calls == [
        (expected_command, '{"request":"typed"}', 41),
    ]
    assert result == ProcessResult(0, '{"answer": "ok"}', "")


def test_should_accept_claude_structured_output_object() -> None:
    provider_output = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "structured_output": {"answer": "typed"},
            "result": "ignored",
        }
    )
    delegate = RecordingRunner(ProcessResult(0, provider_output, ""))
    config = CommandAnalyzerConfig(("claude",), 30, "claude-exec")

    result = structured_cli_runner(config, delegate).run(
        config.command,
        "{}",
        30,
    )

    assert json.loads(result.stdout) == {"answer": "typed"}


@pytest.mark.parametrize(
    "stdout",
    [
        "not-json",
        '{"type":"result","type":"result","subtype":"success",'
        '"is_error":false,"result":"{}"}',
        '{"type":"result","subtype":"failure","is_error":true,"result":"SECRET"}',
        '{"type":"result","subtype":"success","is_error":false,"result":"[]"}',
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"{\\"key\\":1,\\"key\\":2}"}',
    ],
)
def test_should_reject_invalid_envelopes_without_content(stdout: str) -> None:
    delegate = RecordingRunner(ProcessResult(0, stdout, "SECRET"))
    config = CommandAnalyzerConfig(("cursor-agent",), 30, "cursor-exec")

    with pytest.raises(RequirementAnalyzerError) as captured:
        structured_cli_runner(config, delegate).run(config.command, "SECRET", 30)

    assert "SECRET" not in str(captured.value)


def test_should_reject_oversized_provider_output() -> None:
    delegate = RecordingRunner(ProcessResult(0, "x" * 1_000_001, ""))
    config = CommandAnalyzerConfig(("claude",), 30, "claude-exec")

    with pytest.raises(RequirementAnalyzerError, match="output exceeds limit"):
        structured_cli_runner(config, delegate).run(config.command, "{}", 30)


def test_should_preserve_nonzero_result_for_existing_adapter_error() -> None:
    delegate = RecordingRunner(ProcessResult(7, "SECRET", "SECRET"))
    config = CommandAnalyzerConfig(("cursor-agent",), 30, "cursor-exec")

    result = structured_cli_runner(config, delegate).run(config.command, "{}", 30)

    assert result.returncode == 7
