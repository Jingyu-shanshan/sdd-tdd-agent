import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.semantic_review import (
    GeneratedSemanticReview,
    SemanticFinding,
    SemanticReviewError,
    SemanticReviewRequest,
    validate_generated_semantic_review,
)


FINDING_FIELDS = {
    "finding_id",
    "area",
    "severity",
    "file_path",
    "line",
    "message",
    "recommendation",
}
REVIEW_FIELDS = {"summary", "findings", "decision"}
SEMANTIC_REVIEW_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "area": {
                        "type": "string",
                        "enum": [
                            "clean_code",
                            "solid",
                            "duplication",
                            "complexity",
                            "readability",
                            "bug",
                            "performance",
                            "security",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "error"],
                    },
                    "file_path": {"type": "string"},
                    "line": {"type": "integer", "minimum": 1},
                    "message": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": sorted(FINDING_FIELDS),
                "additionalProperties": False,
            },
        },
        "decision": {
            "type": "string",
            "enum": ["approved", "changes_required"],
        },
    },
    "required": sorted(REVIEW_FIELDS),
    "additionalProperties": False,
}


def _request_payload(request: SemanticReviewRequest) -> Dict[str, object]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "completion_sha256": request.completion_sha256,
        "final_test_id": request.final_test_id,
        "sources": [
            {"path": source.path, "content": source.content}
            for source in request.sources
        ],
    }


def _string(record: Dict[str, object], field: str) -> str:
    value = record[field]
    if not isinstance(value, str):
        raise SemanticReviewError(f"Semantic review field has invalid type: {field}")
    return value


def _decode_review(
    content: str,
    request: SemanticReviewRequest,
) -> GeneratedSemanticReview:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise SemanticReviewError("Semantic reviewer returned invalid JSON") from error
    if not isinstance(value, dict) or set(value) != REVIEW_FIELDS:
        raise SemanticReviewError("Semantic reviewer response keys do not match schema")
    payload: Dict[str, object] = value
    finding_values = payload["findings"]
    if not isinstance(finding_values, list):
        raise SemanticReviewError("Semantic review findings have invalid type")
    findings = []
    for item in finding_values:
        if not isinstance(item, dict) or set(item) != FINDING_FIELDS:
            raise SemanticReviewError(
                "Semantic review finding keys do not match schema"
            )
        record: Dict[str, object] = item
        line = record["line"]
        if isinstance(line, bool) or not isinstance(line, int):
            raise SemanticReviewError("Semantic review finding line has invalid type")
        findings.append(
            SemanticFinding(
                finding_id=_string(record, "finding_id"),
                area=_string(record, "area"),
                severity=_string(record, "severity"),
                file_path=_string(record, "file_path"),
                line=line,
                message=_string(record, "message"),
                recommendation=_string(record, "recommendation"),
            )
        )
    generated = GeneratedSemanticReview(
        summary=_string(payload, "summary"),
        findings=tuple(findings),
        decision=_string(payload, "decision"),
    )
    try:
        return validate_generated_semantic_review(request, generated)
    except ValueError as error:
        raise SemanticReviewError(str(error)) from error


class JsonCommandSemanticReviewer:
    """Semantic reviewer using strict JSON stdin/stdout exchange."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def review(self, request: SemanticReviewRequest) -> GeneratedSemanticReview:
        """Exchange one semantic review through an injected shell-free runner."""
        result = self._runner.run(
            self._config.command,
            json.dumps(_request_payload(request), ensure_ascii=False),
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise SemanticReviewError(
                f"Semantic reviewer failed with exit code {result.returncode}"
            )
        return _decode_review(result.stdout, request)


class CodexExecSemanticReviewer:
    """Semantic reviewer backed by isolated ephemeral read-only Codex exec."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        project_root: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex semantic review command needs one executable")
        self._config = config
        self._runner = runner
        self._project_root = project_root.resolve()
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def review(self, request: SemanticReviewRequest) -> GeneratedSemanticReview:
        """Exchange one review from a project-external temporary directory."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(
                prefix="sdd-tdd-semantic-review-"
            ) as directory:
                exchange = Path(directory).resolve()
                if (
                    exchange == self._project_root
                    or self._project_root in exchange.parents
                ):
                    raise SemanticReviewError(
                        "Semantic review workspace is not project-external"
                    )
                schema_path = exchange / "semantic-review.schema.json"
                output_path = exchange / "semantic-review.json"
                schema_path.write_text(
                    json.dumps(SEMANTIC_REVIEW_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path, exchange),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise SemanticReviewError(
                        "Codex semantic reviewer failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_review(
                    output_path.read_text(encoding="utf-8"),
                    request,
                )
        except OSError as error:
            raise SemanticReviewError(
                "Codex semantic review output could not be read"
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
