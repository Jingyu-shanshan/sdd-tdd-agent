import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from sdd_tdd_agent.chat_session import ChatMessage
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    RequirementAnalyzerError,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.skill_catalog import LoadedSkill
from sdd_tdd_agent.workspace_attachments import AttachmentSnapshot


CONVERSATION_ACTIONS = {
    "start_feature",
    "start_bug",
    "advance",
    "approve",
    "reject",
    "show_status",
}
CONVERSATION_KEYS = {"message", "action", "argument"}
CONVERSATION_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "action": {
            "type": ["string", "null"],
            "enum": [None, *sorted(CONVERSATION_ACTIONS)],
        },
        "argument": {"type": ["string", "null"]},
    },
    "required": sorted(CONVERSATION_KEYS),
    "additionalProperties": False,
}
MAX_CONVERSATION_OUTPUT_CHARACTERS = 100_000


@dataclass(frozen=True)
class ConversationRequest:
    """Typed public context supplied to the selected code Provider."""

    prompt_version: str
    prompt: str
    user_message: str
    history: Tuple[ChatMessage, ...]
    workflow_state: Optional[str]
    attachments: Tuple[AttachmentSnapshot, ...] = ()
    skill: Optional[LoadedSkill] = None


@dataclass(frozen=True)
class ConversationReply:
    """Strict Provider reply with at most one validated workflow action."""

    message: str
    action: Optional[str]
    argument: Optional[str]


class ConversationAgent(Protocol):
    """Mockable typed boundary for interactive Provider replies."""

    def respond(self, request: ConversationRequest) -> ConversationReply:
        """Return one validated reply without mutating project state."""
        ...


def _request_payload(request: ConversationRequest) -> Dict[str, object]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "user_message": request.user_message,
        "history": [
            {"role": message.role, "content": message.content}
            for message in request.history
        ],
        "workflow_state": request.workflow_state,
        "attachments": [
            {
                "path": attachment.path,
                "content": attachment.content,
                "sha256": attachment.sha256,
            }
            for attachment in request.attachments
        ],
        "skill": (
            None
            if request.skill is None
            else {
                "name": request.skill.name,
                "content": request.skill.content,
                "source": request.skill.source,
            }
        ),
    }


def _unique_object(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _decode_reply(content: str) -> ConversationReply:
    if len(content) > MAX_CONVERSATION_OUTPUT_CHARACTERS:
        raise RequirementAnalyzerError("Conversation response exceeds limit")
    try:
        payload = json.loads(content, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, ValueError) as error:
        raise RequirementAnalyzerError(
            "Provider returned invalid conversation JSON"
        ) from error
    if not isinstance(payload, dict) or set(payload) != CONVERSATION_KEYS:
        raise RequirementAnalyzerError("Conversation response keys do not match schema")
    message = payload["message"]
    action = payload["action"]
    argument = payload["argument"]
    if not isinstance(message, str) or not message.strip():
        raise RequirementAnalyzerError("Conversation response message is invalid")
    if action is not None and action not in CONVERSATION_ACTIONS:
        raise RequirementAnalyzerError("Conversation response action is invalid")
    if argument is not None and not isinstance(argument, str):
        raise RequirementAnalyzerError("Conversation response argument is invalid")
    if action in {"start_feature", "start_bug", "reject"} and (
        not isinstance(argument, str) or not argument.strip()
    ):
        raise RequirementAnalyzerError(
            "Conversation response action requires an argument"
        )
    if action not in {"start_feature", "start_bug", "reject"} and argument is not None:
        raise RequirementAnalyzerError(
            "Conversation response action does not accept an argument"
        )
    return ConversationReply(message.strip(), action, argument)


class JsonCommandConversationAgent:
    """Conversation agent using the existing strict JSON command protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def respond(self, request: ConversationRequest) -> ConversationReply:
        """Exchange one typed request through the configured Provider."""
        result = self._runner.run(
            self._config.command,
            json.dumps(_request_payload(request), ensure_ascii=False),
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise RequirementAnalyzerError(
                f"Conversation command failed with exit code {result.returncode}"
            )
        return _decode_reply(result.stdout)


class CodexExecConversationAgent:
    """Conversation agent backed by an ephemeral read-only Codex execution."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex conversation command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace.resolve()
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def respond(self, request: ConversationRequest) -> ConversationReply:
        """Exchange one typed request through a read-only Codex process."""
        content = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(prefix="wssagent-chat-") as directory:
                exchange = Path(directory)
                schema_path = exchange / "conversation.schema.json"
                output_path = exchange / "conversation.json"
                schema_path.write_text(
                    json.dumps(CONVERSATION_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    content,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise RequirementAnalyzerError(
                        f"Codex command failed with exit code {result.returncode}"
                    )
                return _decode_reply(output_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise RequirementAnalyzerError(
                "Conversation output could not be read"
            ) from error

    def _command(self, schema_path: Path, output_path: Path) -> Tuple[str, ...]:
        return (
            self._executable,
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
