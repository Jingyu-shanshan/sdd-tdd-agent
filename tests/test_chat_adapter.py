import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.chat_adapter import (
    CodexExecConversationAgent,
    ConversationRequest,
    JsonCommandConversationAgent,
)
from sdd_tdd_agent.chat_session import ChatMessage
from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
)


class RecordingRunner:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        if "--output-last-message" in command:
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps(self.response), encoding="utf-8")
            return ProcessResult(0, "progress", "")
        return ProcessResult(0, json.dumps(self.response), "")


def _request() -> ConversationRequest:
    return ConversationRequest(
        prompt_version="v1",
        prompt="Return a typed response.",
        user_message="Continue",
        history=(ChatMessage("assistant", "Ready."),),
        workflow_state="REQUIREMENT_REVIEW",
    )


def test_should_decode_typed_json_conversation_response() -> None:
    runner = RecordingRunner(
        {
            "message": "I can show the current state.",
            "action": "show_status",
            "argument": None,
        }
    )
    agent = JsonCommandConversationAgent(
        CommandAnalyzerConfig(("bridge",), 30),
        runner,
    )

    reply = agent.respond(_request())

    assert reply.message == "I can show the current state."
    assert reply.action == "show_status"
    assert reply.argument is None
    assert runner.command == ("bridge",)
    assert runner.stdin is not None
    assert json.loads(runner.stdin)["history"] == [
        {"role": "assistant", "content": "Ready."}
    ]


def test_should_reject_unknown_conversation_action() -> None:
    runner = RecordingRunner(
        {"message": "No.", "action": "run_shell", "argument": "rm -rf ."}
    )
    agent = JsonCommandConversationAgent(
        CommandAnalyzerConfig(("bridge",), 30),
        runner,
    )

    with pytest.raises(
        RequirementAnalyzerError,
        match="Conversation response action is invalid",
    ):
        agent.respond(_request())


def test_should_use_ephemeral_read_only_codex_conversation(tmp_path: Path) -> None:
    runner = RecordingRunner({"message": "Ready.", "action": None, "argument": None})
    agent = CodexExecConversationAgent(
        CommandAnalyzerConfig(("codex",), 30, "codex-exec"),
        runner,
        tmp_path,
    )

    reply = agent.respond(_request())

    assert reply.message == "Ready."
    assert runner.command is not None
    assert runner.command[0:2] == ("codex", "exec")
    assert "--ephemeral" in runner.command
    assert runner.command[runner.command.index("--sandbox") + 1] == "read-only"
