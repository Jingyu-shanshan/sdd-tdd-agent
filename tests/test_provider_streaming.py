import json
from pathlib import Path
from typing import Callable, List, Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
)
from sdd_tdd_agent.provider_streaming import (
    ProviderEvent,
    ProviderStreamingRunner,
    parse_provider_event,
    render_provider_event,
)


STREAM_PROTOCOLS = (
    "codex-exec",
    "claude-exec",
    "cursor-exec",
    "pi-exec",
)
MALFORMED_EVENTS = (
    ("codex-exec", '{"type":"item.started","item":[]}'),
    ("claude-exec", '{"type":"stream_event","event":[]}'),
    ("cursor-exec", '{"type":"tool_call","subtype":"started","tool_call":[]}'),
    ("pi-exec", '{"type":"message_update","assistantMessageEvent":[]}'),
)


def test_should_normalize_codex_jsonl_events() -> None:
    started = parse_provider_event(
        "codex-exec",
        json.dumps(
            {
                "type": "item.started",
                "item": {
                    "id": "tool-1",
                    "type": "command_execution",
                    "command": "pytest",
                },
            }
        ),
    )
    finished = parse_provider_event(
        "codex-exec",
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "tool-1",
                    "type": "command_execution",
                    "exit_code": 0,
                    "aggregated_output": "1 passed",
                },
            }
        ),
    )

    assert started == (ProviderEvent("tool_started", "tool-1", "command"),)
    assert finished == (
        ProviderEvent(
            "tool_output",
            "tool-1",
            "command",
            text="1 passed",
        ),
        ProviderEvent("tool_finished", "tool-1", "command", exit_code=0),
    )


def test_should_normalize_claude_partial_text_without_thinking() -> None:
    text = parse_provider_event(
        "claude-exec",
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Hello"},
                },
            }
        ),
    )
    thinking = parse_provider_event(
        "claude-exec",
        json.dumps(
            {
                "type": "stream_event",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "thinking_delta", "thinking": "secret"},
                },
            }
        ),
    )

    assert text == (ProviderEvent("message_delta", text="Hello"),)
    assert thinking == ()


def test_should_normalize_cursor_and_pi_tool_events() -> None:
    cursor = parse_provider_event(
        "cursor-exec",
        json.dumps(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-1",
                "tool_call": {"readToolCall": {"args": {"path": "README.md"}}},
            }
        ),
    )
    pi = parse_provider_event(
        "pi-exec",
        json.dumps(
            {
                "type": "tool_execution_end",
                "toolCallId": "call-2",
                "toolName": "bash",
                "isError": False,
            }
        ),
    )

    assert cursor == (ProviderEvent("tool_started", "call-1", "read"),)
    assert pi == (ProviderEvent("tool_finished", "call-2", "bash", exit_code=0),)


@pytest.mark.parametrize("protocol", STREAM_PROTOCOLS)
def test_should_ignore_unknown_event_and_reject_malformed_json(
    protocol: str,
) -> None:
    assert parse_provider_event(protocol, '{"type":"future_event"}') == ()

    with pytest.raises(RequirementAnalyzerError, match="invalid JSONL"):
        parse_provider_event(protocol, "{")


@pytest.mark.parametrize(("protocol", "event"), MALFORMED_EVENTS)
def test_should_reject_malformed_known_event(
    protocol: str,
    event: str,
) -> None:
    with pytest.raises(RequirementAnalyzerError, match="invalid JSONL"):
        parse_provider_event(protocol, event)


class FakeStreamingProcess:
    def __init__(self, lines: List[str], returncode: int = 0) -> None:
        self.lines = lines
        self.returncode = returncode
        self.command: Tuple[str, ...] = ()
        self.stdin = ""

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        for line in self.lines:
            on_stdout_line(line)
        return ProcessResult(self.returncode, "\n".join(self.lines), "")


def test_should_stream_claude_and_return_only_terminal_result() -> None:
    process = FakeStreamingProcess(
        [
            json.dumps({"type": "system", "subtype": "init"}),
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "result": '{"message":"done"}',
                }
            ),
        ]
    )
    events: List[ProviderEvent] = []
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig(("claude",), 30, "claude-exec"),
        process,
        events.append,
    )

    result = runner.run(
        (
            "claude",
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "plan",
            "--no-session-persistence",
        ),
        "{}",
        30,
    )

    assert "--output-format" in process.command
    assert process.command[process.command.index("--output-format") + 1] == (
        "stream-json"
    )
    assert "--include-partial-messages" in process.command
    assert json.loads(result.stdout)["type"] == "result"


def test_should_enable_codex_jsonl_without_changing_terminal_output() -> None:
    process = FakeStreamingProcess([])
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig(("codex",), 30, "codex-exec"),
        process,
        lambda event: None,
    )

    result = runner.run(
        ("codex", "exec", "--ephemeral", "--output-last-message", "result.json"),
        "{}",
        30,
    )

    assert process.command[0:3] == ("codex", "exec", "--json")
    assert result.returncode == 0


def test_should_use_pi_rpc_and_return_final_assistant_text() -> None:
    process = FakeStreamingProcess(
        [
            json.dumps(
                {
                    "type": "message_end",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": '{"ok":true}'}],
                    },
                }
            ),
            json.dumps({"type": "agent_settled"}),
        ]
    )
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig(("pi",), 30, "pi-exec"),
        process,
        lambda event: None,
    )

    result = runner.run(("pi", "-p", "--no-session"), "typed request", 30)

    assert process.command[0:3] == ("pi", "--mode", "rpc")
    assert json.loads(process.stdin)["type"] == "prompt"
    assert result.stdout == '{"ok":true}'


def test_should_fail_when_stream_has_no_terminal_result(tmp_path: Path) -> None:
    del tmp_path
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig(("cursor-agent",), 30, "cursor-exec"),
        FakeStreamingProcess([json.dumps({"type": "system", "subtype": "init"})]),
        lambda event: None,
    )

    with pytest.raises(RequirementAnalyzerError, match="terminal result"):
        runner.run(
            ("cursor-agent", "-p", "--output-format", "json"),
            "{}",
            30,
        )


@pytest.mark.parametrize(
    ("protocol", "command"),
    [
        ("codex-exec", ("codex", "exec", "--ephemeral")),
        ("claude-exec", ("claude", "-p", "--output-format", "json")),
        ("cursor-exec", ("cursor-agent", "-p", "--output-format", "json")),
        ("pi-exec", ("pi", "-p", "--no-session")),
    ],
)
def test_should_report_nonzero_provider_exit(
    protocol: str,
    command: Tuple[str, ...],
) -> None:
    events: List[ProviderEvent] = []
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig((command[0],), 30, protocol),
        FakeStreamingProcess([], returncode=7),
        events.append,
    )

    result = runner.run(command, "{}", 30)

    assert result == ProcessResult(7, "", "")
    assert events == [
        ProviderEvent(
            "error",
            text="Provider exited with code 7",
            exit_code=7,
        )
    ]


def test_should_render_only_sanitized_public_stream_content(
    tmp_path: Path,
) -> None:
    event = ProviderEvent(
        "tool_output",
        text=f"{tmp_path}/secret.txt token=private",
    )

    assert render_provider_event(tmp_path, event, verbose=False) == (
        "[output folded]\n"
    )
    assert render_provider_event(tmp_path, event, verbose=True) == (
        "[output] <PROJECT_ROOT>/secret.txt token=<REDACTED>\n"
    )
    unsafe_tool = ProviderEvent(
        "tool_started",
        tool_name="\x1b[31mcommand token=private",
    )
    assert render_provider_event(tmp_path, unsafe_tool, verbose=False) == (
        "[tool] command token=<REDACTED> started\n"
    )
