import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    ProcessRunner,
    RequirementAnalyzerError,
)
from sdd_tdd_agent.streaming_process import StreamingProcessRunner
from sdd_tdd_agent.red_execution import sanitize_public_text


EVENT_KINDS = {
    "message_delta",
    "progress",
    "tool_started",
    "tool_output",
    "tool_finished",
    "result",
    "error",
    "usage",
}
MAX_JSONL_LINE_CHARACTERS = 1_000_000


@dataclass(frozen=True)
class ProviderEvent:
    """One normalized public Provider stream event."""

    kind: str
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    text: Optional[str] = None
    exit_code: Optional[int] = None
    usage: Tuple[Tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError("Provider event kind is invalid")


def _unique_object(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _payload(line: str) -> Dict[str, object]:
    if len(line) > MAX_JSONL_LINE_CHARACTERS:
        raise RequirementAnalyzerError("Provider returned oversized JSONL event")
    try:
        value = json.loads(line, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, ValueError) as error:
        raise RequirementAnalyzerError(
            "Provider returned invalid JSONL event"
        ) from error
    if not isinstance(value, dict):
        raise RequirementAnalyzerError("Provider JSONL event must be an object")
    return value


def parse_provider_event(
    protocol: str,
    line: str,
) -> Tuple[ProviderEvent, ...]:
    """Normalize one Provider JSONL record and ignore unknown event types."""
    payload = _payload(line)
    if protocol == "codex-exec":
        return _codex_events(payload)
    if protocol == "claude-exec":
        return _claude_events(payload)
    if protocol == "cursor-exec":
        return _cursor_events(payload)
    if protocol == "pi-exec":
        return _pi_events(payload)
    raise RequirementAnalyzerError("Provider streaming protocol is unsupported")


def render_provider_event(
    root: Path,
    event: ProviderEvent,
    verbose: bool,
) -> str:
    """Render one sanitized public event without exposing hidden reasoning."""
    text = (
        sanitize_public_text(root, event.text)[:2_000] if event.text is not None else ""
    )
    tool_name = sanitize_public_text(root, event.tool_name or "tool")[:200]
    if event.kind == "message_delta":
        return f"[delta] {text}\n" if verbose and text else ""
    if event.kind == "progress":
        return f"[provider] {text}\n" if text else ""
    if event.kind == "tool_started":
        return f"[tool] {tool_name} started\n"
    if event.kind == "tool_output":
        return f"[output] {text}\n" if verbose and text else "[output folded]\n"
    if event.kind == "tool_finished":
        code = "unknown" if event.exit_code is None else str(event.exit_code)
        return f"[tool] {tool_name} finished (exit {code})\n"
    if event.kind == "result":
        return "[provider] complete\n"
    if event.kind == "error":
        return f"Error: {text or 'Provider failed'}\n"
    usage = ", ".join(
        f"{sanitize_public_text(root, key)[:200]}={value}" for key, value in event.usage
    )
    return f"[usage] {usage}\n" if usage else ""


class ProviderStreamingRunner(ProcessRunner):
    """Adapt one Provider JSONL process to the existing final-result boundary."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        delegate: StreamingProcessRunner,
        event_sink: Callable[[ProviderEvent], None],
    ) -> None:
        self._config = config
        self._delegate = delegate
        self._event_sink = event_sink

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        """Stream public events while returning only the trusted terminal result."""
        if self._config.protocol == "json-command":
            raise RequirementAnalyzerError(
                "Custom JSON commands do not support Provider streaming"
            )
        terminal: List[Dict[str, object]] = []
        pi_messages: List[str] = []
        pi_settled = [False]

        def on_line(line: str) -> None:
            payload = _payload(line)
            for event in parse_provider_event(self._config.protocol, line):
                self._event_sink(event)
            if self._config.protocol in {"claude-exec", "cursor-exec"}:
                if payload.get("type") == "result":
                    terminal[:] = [payload]
            elif self._config.protocol == "pi-exec":
                message = _pi_assistant_message(payload)
                if message is not None:
                    pi_messages.append(message)
                if payload.get("type") == "agent_settled":
                    pi_settled[0] = True

        transformed, transformed_stdin = _stream_command(
            self._config.protocol,
            command,
            stdin,
        )
        result = self._delegate.run(
            transformed,
            transformed_stdin,
            timeout_seconds,
            on_line,
        )
        if result.returncode != 0:
            self._event_sink(
                ProviderEvent(
                    "error",
                    text=f"Provider exited with code {result.returncode}",
                    exit_code=result.returncode,
                )
            )
            return ProcessResult(result.returncode, "", "")
        if self._config.protocol == "codex-exec":
            return result
        if self._config.protocol in {"claude-exec", "cursor-exec"}:
            if len(terminal) != 1:
                raise RequirementAnalyzerError("Provider stream has no terminal result")
            return ProcessResult(0, json.dumps(terminal[0]), "")
        if not pi_settled[0] or not pi_messages:
            raise RequirementAnalyzerError("Provider stream has no terminal result")
        return ProcessResult(0, pi_messages[-1], "")


def _stream_command(
    protocol: str,
    command: Tuple[str, ...],
    stdin: str,
) -> Tuple[Tuple[str, ...], str]:
    if protocol == "codex-exec":
        if len(command) < 2 or command[1] != "exec":
            raise RequirementAnalyzerError("Provider streaming command is invalid")
        arguments = list(command)
        if "--json" not in arguments:
            arguments.insert(2, "--json")
        return tuple(arguments), stdin
    if protocol in {"claude-exec", "cursor-exec"}:
        arguments = list(command)
        try:
            index = arguments.index("--output-format")
            arguments[index + 1] = "stream-json"
        except (ValueError, IndexError) as error:
            raise RequirementAnalyzerError(
                "Provider streaming command is invalid"
            ) from error
        if protocol == "claude-exec":
            arguments.extend(("--verbose", "--include-partial-messages"))
        return tuple(arguments), stdin
    if protocol == "pi-exec":
        rpc_command = (
            command[0],
            "--mode",
            "rpc",
            "--no-session",
            "--no-tools",
            "--no-context-files",
            "--no-extensions",
            "--no-skills",
            "--no-prompt-templates",
            "--no-approve",
        )
        request = json.dumps(
            {"id": "wssagent", "type": "prompt", "message": stdin},
            ensure_ascii=False,
        )
        return rpc_command, request + "\n"
    raise RequirementAnalyzerError("Provider streaming protocol is unsupported")


def _codex_events(payload: Dict[str, object]) -> Tuple[ProviderEvent, ...]:
    event_type = payload.get("type")
    if event_type in {"thread.started", "turn.started"}:
        return (ProviderEvent("progress", text=str(event_type)),)
    if event_type == "turn.completed":
        events = [ProviderEvent("result")]
        usage = _usage(payload.get("usage"))
        if usage:
            events.append(ProviderEvent("usage", usage=usage))
        return tuple(events)
    if event_type in {"error", "turn.failed"}:
        return (ProviderEvent("error", text=_error_text(payload)),)
    if event_type not in {"item.started", "item.completed"}:
        return ()
    item = payload.get("item")
    if not isinstance(item, dict):
        raise RequirementAnalyzerError("Provider returned invalid JSONL event")
    item_type = item.get("type")
    if item_type == "agent_message" and event_type == "item.completed":
        text = item.get("text")
        return (
            (ProviderEvent("message_delta", text=text),)
            if isinstance(text, str)
            else ()
        )
    if item_type == "reasoning" and event_type == "item.completed":
        summary = item.get("summary")
        return (
            (ProviderEvent("progress", text=summary),)
            if isinstance(summary, str)
            else ()
        )
    tool_name = {
        "command_execution": "command",
        "file_change": "file change",
        "mcp_tool_call": "MCP",
        "web_search": "web search",
    }.get(str(item_type))
    if tool_name is None:
        return ()
    tool_id = _optional_string(item.get("id"))
    if event_type == "item.started":
        return (ProviderEvent("tool_started", tool_id, tool_name),)
    events: List[ProviderEvent] = []
    output = item.get("aggregated_output")
    if isinstance(output, str) and output:
        events.append(ProviderEvent("tool_output", tool_id, tool_name, text=output))
    exit_code = item.get("exit_code")
    code = exit_code if isinstance(exit_code, int) else None
    events.append(ProviderEvent("tool_finished", tool_id, tool_name, exit_code=code))
    return tuple(events)


def _claude_events(payload: Dict[str, object]) -> Tuple[ProviderEvent, ...]:
    event_type = payload.get("type")
    if event_type == "system":
        return (ProviderEvent("progress", text="provider initialized"),)
    if event_type == "result":
        events = [ProviderEvent("result", text=_optional_string(payload.get("result")))]
        usage = _usage(payload.get("usage"))
        if usage:
            events.append(ProviderEvent("usage", usage=usage))
        return tuple(events)
    if event_type != "stream_event":
        return ()
    event = payload.get("event")
    if not isinstance(event, dict):
        raise RequirementAnalyzerError("Provider returned invalid JSONL event")
    nested_type = event.get("type")
    if nested_type == "content_block_delta":
        delta = event.get("delta")
        if not isinstance(delta, dict) or delta.get("type") != "text_delta":
            return ()
        text = delta.get("text")
        return (
            (ProviderEvent("message_delta", text=text),)
            if isinstance(text, str)
            else ()
        )
    if nested_type == "content_block_start":
        block = event.get("content_block")
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            return ()
        return (
            ProviderEvent(
                "tool_started",
                _optional_string(block.get("id")),
                _optional_string(block.get("name")) or "tool",
            ),
        )
    return ()


def _cursor_events(payload: Dict[str, object]) -> Tuple[ProviderEvent, ...]:
    event_type = payload.get("type")
    if event_type == "system":
        return (ProviderEvent("progress", text="provider initialized"),)
    if event_type == "assistant":
        message = payload.get("message")
        return tuple(
            ProviderEvent("message_delta", text=text) for text in _content_text(message)
        )
    if event_type == "result":
        return (
            ProviderEvent(
                "result",
                text=_optional_string(payload.get("result")),
            ),
        )
    if event_type != "tool_call":
        return ()
    tool_call = payload.get("tool_call")
    if not isinstance(tool_call, dict) or not tool_call:
        raise RequirementAnalyzerError("Provider returned invalid JSONL event")
    call_id = _optional_string(payload.get("call_id"))
    name = _cursor_tool_name(tool_call)
    subtype = payload.get("subtype")
    if subtype == "started":
        return (ProviderEvent("tool_started", call_id, name),)
    if subtype == "completed":
        return (ProviderEvent("tool_finished", call_id, name, exit_code=0),)
    return ()


def _pi_events(payload: Dict[str, object]) -> Tuple[ProviderEvent, ...]:
    event_type = payload.get("type")
    if event_type in {"agent_start", "turn_start"}:
        return (ProviderEvent("progress", text=str(event_type)),)
    if event_type == "agent_settled":
        return (ProviderEvent("result"),)
    if event_type == "message_update":
        update = payload.get("assistantMessageEvent")
        if not isinstance(update, dict):
            raise RequirementAnalyzerError("Provider returned invalid JSONL event")
        if update.get("type") != "text_delta":
            return ()
        text = update.get("delta")
        return (
            (ProviderEvent("message_delta", text=text),)
            if isinstance(text, str)
            else ()
        )
    tool_id = _optional_string(payload.get("toolCallId"))
    tool_name = _optional_string(payload.get("toolName")) or "tool"
    if event_type == "tool_execution_start":
        return (ProviderEvent("tool_started", tool_id, tool_name),)
    if event_type == "tool_execution_update":
        text = "\n".join(_content_text(payload.get("partialResult")))
        return (
            (ProviderEvent("tool_output", tool_id, tool_name, text=text),)
            if text
            else ()
        )
    if event_type == "tool_execution_end":
        exit_code = 1 if payload.get("isError") is True else 0
        return (
            ProviderEvent(
                "tool_finished",
                tool_id,
                tool_name,
                exit_code=exit_code,
            ),
        )
    if event_type == "extension_error":
        return (ProviderEvent("error", text=_error_text(payload)),)
    return ()


def _pi_assistant_message(payload: Dict[str, object]) -> Optional[str]:
    if payload.get("type") != "message_end":
        return None
    message = payload.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return None
    content = _content_text(message)
    return "".join(content) if content else None


def _content_text(value: object) -> Tuple[str, ...]:
    if isinstance(value, dict):
        value = value.get("content")
    if not isinstance(value, list):
        return ()
    return tuple(
        item["text"]
        for item in value
        if isinstance(item, dict)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
    )


def _cursor_tool_name(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "tool"
    key = next(iter(value))
    return key.removesuffix("ToolCall") or "tool"


def _usage(value: object) -> Tuple[Tuple[str, int], ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(
        sorted(
            (key, item)
            for key, item in value.items()
            if isinstance(key, str) and isinstance(item, int)
        )
    )


def _error_text(payload: Dict[str, object]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        error = error.get("message")
    if isinstance(error, str):
        return error
    message = payload.get("message")
    return message if isinstance(message, str) else "Provider reported an error"


def _optional_string(value: object) -> Optional[str]:
    return value if isinstance(value, str) and value else None
