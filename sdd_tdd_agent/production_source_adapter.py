import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, cast

from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    RequirementAnalyzerError,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.production_source_generation import (
    GeneratedProductionSource,
    ProductionSourceGenerationRequest,
    validate_generated_production_source,
)
from sdd_tdd_agent.test_generation import TestCasePlan


RESPONSE_FIELDS = ("test_id", "file_path", "content")
PRODUCTION_SOURCE_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "test_id": {"type": "string"},
        "file_path": {"type": "string"},
        "content": {"type": "string"},
    },
    "required": list(RESPONSE_FIELDS),
    "additionalProperties": False,
}


class ProductionSourceGeneratorError(RequirementAnalyzerError):
    """Safe public error raised by a production-source adapter."""

    __test__ = False


def _case_payload(case: TestCasePlan) -> Dict[str, object]:
    return {
        "test_id": case.test_id,
        "task_id": case.task_id,
        "phase": case.phase,
        "title": case.title,
        "objective": case.objective,
        "test_file": case.test_file,
        "test_name": case.test_name,
        "preconditions": list(case.preconditions),
        "action": case.action,
        "expected_outcomes": list(case.expected_outcomes),
        "dependencies": list(case.dependencies),
    }


def _request_payload(
    request: ProductionSourceGenerationRequest,
) -> Dict[str, object]:
    context = request.context
    current_source = context.current_test_source
    if current_source is None:
        raise ProductionSourceGeneratorError("Current test source is missing")
    payload = {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "current_test": _case_payload(context.current_test),
        "current_test_source": {
            "path": current_source.path,
            "content": current_source.content,
        },
        "production_sources": [
            {"path": snapshot.path, "content": snapshot.content}
            for snapshot in context.production_sources
        ],
        "compile_output": context.compile_output,
        "test_output": context.test_output,
    }
    if request.prompt_version != "v1":
        payload["production_source_roots"] = list(request.production_source_roots)
    return payload


def _decode_source(
    content: str,
    request: ProductionSourceGenerationRequest,
) -> GeneratedProductionSource:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ProductionSourceGeneratorError(
            "Production source generator returned invalid JSON"
        ) from error
    if not isinstance(value, dict):
        raise ProductionSourceGeneratorError(
            "Production source generator response must be a JSON object"
        )
    payload: Dict[str, object] = value
    if set(payload) != set(RESPONSE_FIELDS):
        raise ProductionSourceGeneratorError(
            "Production source generator response keys do not match schema"
        )
    for field in RESPONSE_FIELDS:
        if not isinstance(payload[field], str):
            raise ProductionSourceGeneratorError(
                f"Production source generator field has invalid type: {field}"
            )
    generated = GeneratedProductionSource(
        cast(str, payload["test_id"]),
        cast(str, payload["file_path"]),
        cast(str, payload["content"]),
    )
    try:
        return validate_generated_production_source(request, generated)
    except ValueError as error:
        raise ProductionSourceGeneratorError(str(error)) from error


class JsonCommandProductionSourceGenerator:
    """Blind production generator using strict JSON stdin/stdout."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def generate(
        self,
        request: ProductionSourceGenerationRequest,
    ) -> GeneratedProductionSource:
        """Exchange one Blind request through an injected shell-free runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise ProductionSourceGeneratorError(
                f"Production source generator failed with exit code {result.returncode}"
            )
        return _decode_source(result.stdout, request)


class CodexExecProductionSourceGenerator:
    """Blind generator backed by isolated ephemeral read-only Codex exec."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        project_root: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex production source command needs one executable")
        self._config = config
        self._runner = runner
        self._project_root = project_root.resolve()
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def generate(
        self,
        request: ProductionSourceGenerationRequest,
    ) -> GeneratedProductionSource:
        """Exchange one Blind request from a project-external directory."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(
                prefix="sdd-tdd-blind-production-"
            ) as directory:
                exchange = Path(directory).resolve()
                if (
                    exchange == self._project_root
                    or self._project_root in exchange.parents
                ):
                    raise ProductionSourceGeneratorError(
                        "Blind production workspace is not project-external"
                    )
                schema_path = exchange / "production-source.schema.json"
                output_path = exchange / "production-source.json"
                schema_path.write_text(
                    json.dumps(PRODUCTION_SOURCE_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path, exchange),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise ProductionSourceGeneratorError(
                        "Codex production source command failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_source(
                    output_path.read_text(encoding="utf-8"),
                    request,
                )
        except OSError as error:
            raise ProductionSourceGeneratorError(
                "Codex production source output could not be read"
            ) from error

    def _command(
        self,
        schema_path: Path,
        output_path: Path,
        workspace: Path,
    ) -> Tuple[str, ...]:
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
            str(workspace),
            "-",
        )
