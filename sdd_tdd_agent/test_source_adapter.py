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
from sdd_tdd_agent.test_generation import TestCasePlan
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    TestSourceGenerationRequest,
    validate_generated_test_source,
)


RESPONSE_FIELDS = ("test_id", "file_path", "content")
TEST_SOURCE_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "test_id": {"type": "string"},
        "file_path": {"type": "string"},
        "content": {"type": "string"},
    },
    "required": list(RESPONSE_FIELDS),
    "additionalProperties": False,
}


class TestSourceGeneratorError(RequirementAnalyzerError):
    """Safe public error raised by a single-test source adapter."""

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


def _request_payload(request: TestSourceGenerationRequest) -> Dict[str, object]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "requirement": request.requirement,
        "design": request.design,
        "current_test": _case_payload(request.current_test),
        "sources": [
            {"path": snapshot.path, "content": snapshot.content}
            for snapshot in request.sources
        ],
    }


def _decode_source(
    content: str,
    request: TestSourceGenerationRequest,
) -> GeneratedTestSource:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise TestSourceGeneratorError(
            "Test source generator returned invalid JSON"
        ) from error
    if not isinstance(value, dict):
        raise TestSourceGeneratorError(
            "Test source generator response must be a JSON object"
        )
    payload: Dict[str, object] = value
    if set(payload) != set(RESPONSE_FIELDS):
        raise TestSourceGeneratorError(
            "Test source generator response keys do not match schema"
        )
    for field in RESPONSE_FIELDS:
        if not isinstance(payload[field], str):
            raise TestSourceGeneratorError(
                f"Test source generator field has invalid type: {field}"
            )
    generated = GeneratedTestSource(
        test_id=cast(str, payload["test_id"]),
        file_path=cast(str, payload["file_path"]),
        content=cast(str, payload["content"]),
    )
    return validate_generated_test_source(request, generated)


class JsonCommandTestSourceGenerator:
    """Single-test generator using the strict provider-neutral JSON protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def generate(self, request: TestSourceGenerationRequest) -> GeneratedTestSource:
        """Exchange one isolated test-source request through the runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise TestSourceGeneratorError(
                "Test source generator command failed with exit code "
                f"{result.returncode}"
            )
        return _decode_source(result.stdout, request)


class CodexExecTestSourceGenerator:
    """Single-test generator backed by an ephemeral read-only Codex CLI run."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex test source command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def generate(self, request: TestSourceGenerationRequest) -> GeneratedTestSource:
        """Exchange one test-source request through structured Codex exec."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(
                prefix="sdd-tdd-codex-test-source-"
            ) as path:
                exchange = Path(path)
                schema_path = exchange / "test-source.schema.json"
                output_path = exchange / "test-source.json"
                schema_path.write_text(
                    json.dumps(TEST_SOURCE_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise TestSourceGeneratorError(
                        "Codex test source command failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_source(
                    output_path.read_text(encoding="utf-8"),
                    request,
                )
        except OSError as error:
            raise TestSourceGeneratorError(
                "Codex test source output could not be read"
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
