import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from sdd_tdd_agent.design_generation import (
    DesignGenerationRequest,
    DesignProposal,
)
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    RequirementAnalyzerError,
    SystemCodexCommandResolver,
)


DESIGN_FIELDS = (
    "overview",
    "architecture_decisions",
    "components",
    "data_flow",
    "interfaces",
    "error_handling",
    "security_considerations",
    "testing_strategy",
    "risks_and_tradeoffs",
    "open_questions",
)

DESIGN_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "architecture_decisions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "components": {"type": "array", "items": {"type": "string"}},
        "data_flow": {"type": "array", "items": {"type": "string"}},
        "interfaces": {"type": "array", "items": {"type": "string"}},
        "error_handling": {"type": "array", "items": {"type": "string"}},
        "security_considerations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "testing_strategy": {"type": "array", "items": {"type": "string"}},
        "risks_and_tradeoffs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(DESIGN_FIELDS),
    "additionalProperties": False,
}


class DesignGeneratorError(RequirementAnalyzerError):
    """Safe public error raised by a design generator adapter."""


def _request_payload(request: DesignGenerationRequest) -> Dict[str, str]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "requirement": request.requirement,
        "project_metadata": request.project_metadata,
        "architecture": request.architecture,
        "conventions": request.conventions,
    }


def _string_tuple(payload: Dict[str, object], key: str) -> Tuple[str, ...]:
    value = payload[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise DesignGeneratorError(f"Design generator field has invalid type: {key}")
    return tuple(value)


def _decode_proposal(content: str) -> DesignProposal:
    try:
        payload_value = json.loads(content)
    except json.JSONDecodeError as error:
        raise DesignGeneratorError("Design generator returned invalid JSON") from error
    if not isinstance(payload_value, dict):
        raise DesignGeneratorError("Design generator response must be a JSON object")
    payload: Dict[str, object] = payload_value
    if set(payload) != set(DESIGN_FIELDS):
        raise DesignGeneratorError("Design generator response keys do not match schema")
    overview = payload["overview"]
    if not isinstance(overview, str):
        raise DesignGeneratorError("Design generator field has invalid type: overview")
    return DesignProposal(
        overview=overview,
        architecture_decisions=_string_tuple(payload, "architecture_decisions"),
        components=_string_tuple(payload, "components"),
        data_flow=_string_tuple(payload, "data_flow"),
        interfaces=_string_tuple(payload, "interfaces"),
        error_handling=_string_tuple(payload, "error_handling"),
        security_considerations=_string_tuple(
            payload,
            "security_considerations",
        ),
        testing_strategy=_string_tuple(payload, "testing_strategy"),
        risks_and_tradeoffs=_string_tuple(payload, "risks_and_tradeoffs"),
        open_questions=_string_tuple(payload, "open_questions"),
    )


class JsonCommandDesignGenerator:
    """Design generator using the strict provider-neutral JSON protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
        """Exchange one typed design request through the configured runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise DesignGeneratorError(
                f"Design generator command failed with exit code {result.returncode}"
            )
        return _decode_proposal(result.stdout)


class CodexExecDesignGenerator:
    """Design generator backed by an ephemeral read-only Codex CLI run."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex design command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
        """Exchange one design request through a structured Codex exec run."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(prefix="sdd-tdd-codex-design-") as path:
                exchange = Path(path)
                schema_path = exchange / "design.schema.json"
                output_path = exchange / "design.json"
                schema_path.write_text(json.dumps(DESIGN_SCHEMA), encoding="utf-8")
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise DesignGeneratorError(
                        f"Codex design command failed with exit code {result.returncode}"
                    )
                return _decode_proposal(output_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise DesignGeneratorError(
                "Codex design output could not be read"
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
