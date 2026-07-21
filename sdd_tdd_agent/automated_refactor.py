import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Optional, Protocol, Tuple, cast

from sdd_tdd_agent.cycle_completion import canonical_json_sha256
from sdd_tdd_agent.model_adapter import (
    CodexCommandResolver,
    CommandAnalyzerConfig,
    ProcessRunner,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    RedExecutionError,
    TestCommandRunner,
)
from sdd_tdd_agent.refactor_completion import (
    RefactorVerificationError,
    _RefactorContext,
    _load_context,
    complete_active_refactor,
)
from sdd_tdd_agent.tdd_cycle import SourceSnapshot


PROMPT_VERSION = "v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "automated_refactor" / "v1.md"
MAX_SOURCE_BYTES = 1_000_000
MAX_SUMMARY_CHARACTERS = 4_000
SENSITIVE_OUTPUT_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]")
RESPONSE_FIELDS = {"file_path", "content", "summary"}
AUTOMATED_REFACTOR_FIELDS = {
    "file_path",
    "before_sha256",
    "after_sha256",
    "completion_sha256",
    "review_sha256",
}
AUTOMATED_REFACTOR_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string"},
        "content": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": sorted(RESPONSE_FIELDS),
    "additionalProperties": False,
}


class AutomatedRefactorError(RuntimeError):
    """Safe public error for automated behavior-preserving refactoring."""


@dataclass(frozen=True)
class AutomatedRefactorRequest:
    """Digest-bound context for one exact production-source refactor."""

    __test__: ClassVar[bool] = False

    prompt_version: str
    prompt: str
    completion_sha256: str
    review_sha256: str
    review: str
    source: SourceSnapshot


@dataclass(frozen=True)
class GeneratedAutomatedRefactor:
    """One complete same-path behavior-preserving source replacement."""

    file_path: str
    content: str
    summary: str


class AutomatedRefactorGenerator(Protocol):
    """Typed and mockable model boundary for one source refactor."""

    def generate(
        self,
        request: AutomatedRefactorRequest,
    ) -> GeneratedAutomatedRefactor:
        """Generate one complete same-path source replacement."""
        ...


@dataclass(frozen=True)
class AutomatedRefactorRun:
    """Result of a generated refactor accepted by both final test gates."""

    session_id: str
    file_path: str
    before_sha256: str
    after_sha256: str


def _source_path(root: Path, file_path: str) -> Path:
    relative = PurePosixPath(file_path.replace("\\", "/"))
    if file_path != relative.as_posix() or relative.is_absolute():
        raise AutomatedRefactorError("Final production source path is unsafe")
    target = root.resolve()
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise AutomatedRefactorError("Final production source changed")
    return target


def _production_path(context: _RefactorContext) -> str:
    artifact = context.state.get("production_source")
    if not isinstance(artifact, dict):
        raise AutomatedRefactorError("Final production artifact is invalid")
    value = artifact.get("file_path")
    if not isinstance(value, str):
        raise AutomatedRefactorError("Final production artifact is invalid")
    return value


def _review_digest(context: _RefactorContext) -> str:
    review = context.state.get("implementation_review")
    if (
        not isinstance(review, dict)
        or review.get("decision") != "semantic_review_passed"
    ):
        raise AutomatedRefactorError(
            "Automated refactor requires an approved semantic review"
        )
    digest = review.get("report_sha256")
    if not isinstance(digest, str):
        raise AutomatedRefactorError("Implementation review is invalid")
    return digest


def _request_from_context(
    root: Path,
    context: _RefactorContext,
) -> AutomatedRefactorRequest:
    file_path = _production_path(context)
    source_path = _source_path(root, file_path)
    review_path = context.state_path.parent / "review.md"
    try:
        content = source_path.read_text(encoding="utf-8")
        review = review_path.read_text(encoding="utf-8")
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise AutomatedRefactorError("Refactor input could not be read") from error
    if review_path.is_symlink():
        raise AutomatedRefactorError("Implementation review changed")
    return AutomatedRefactorRequest(
        PROMPT_VERSION,
        prompt,
        canonical_json_sha256(context.state["implementation_completion"]),
        _review_digest(context),
        review,
        SourceSnapshot(file_path, content),
    )


def load_automated_refactor_request(
    root: Path,
    session_id: str,
) -> AutomatedRefactorRequest:
    """Load one exact refactor request from an approved semantic audit chain."""
    try:
        context = _load_context(root, session_id)
    except RefactorVerificationError as error:
        raise AutomatedRefactorError(str(error)) from error
    return _request_from_context(root, context)


def validate_generated_automated_refactor(
    request: AutomatedRefactorRequest,
    generated: GeneratedAutomatedRefactor,
) -> GeneratedAutomatedRefactor:
    """Validate one generated result against the exact visible source."""
    if not isinstance(request, AutomatedRefactorRequest):
        raise ValueError("Automated refactor request is invalid")
    if not isinstance(generated, GeneratedAutomatedRefactor):
        raise ValueError("Automated refactor result is invalid")
    if generated.file_path != request.source.path:
        raise ValueError(
            "Automated refactor must replace the exact final production file"
        )
    if not isinstance(generated.content, str) or not generated.content.strip():
        raise ValueError("Automated refactor content is empty")
    if "\0" in generated.content:
        raise ValueError("Automated refactor content contains a null byte")
    try:
        size = len(generated.content.encode("utf-8"))
    except UnicodeError as error:
        raise ValueError("Automated refactor content must be valid UTF-8") from error
    if size > MAX_SOURCE_BYTES:
        raise ValueError("Automated refactor content is too large")
    if generated.content == request.source.content:
        raise ValueError("Automated refactor must change the source")
    if (
        not isinstance(generated.summary, str)
        or not generated.summary.strip()
        or len(generated.summary) > MAX_SUMMARY_CHARACTERS
        or "\0" in generated.summary
        or SENSITIVE_OUTPUT_PATTERN.search(generated.summary) is not None
    ):
        raise ValueError("Automated refactor summary is invalid")
    return generated


def _request_payload(request: AutomatedRefactorRequest) -> Dict[str, object]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "completion_sha256": request.completion_sha256,
        "review_sha256": request.review_sha256,
        "review": request.review,
        "source": {
            "path": request.source.path,
            "content": request.source.content,
        },
    }


def _decode_refactor(
    content: str,
    request: AutomatedRefactorRequest,
) -> GeneratedAutomatedRefactor:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise AutomatedRefactorError(
            "Refactor generator returned invalid JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != RESPONSE_FIELDS:
        raise AutomatedRefactorError("Refactor response keys do not match schema")
    payload: Dict[str, object] = value
    if any(not isinstance(payload[field], str) for field in RESPONSE_FIELDS):
        raise AutomatedRefactorError("Refactor response field has invalid type")
    generated = GeneratedAutomatedRefactor(
        cast(str, payload["file_path"]),
        cast(str, payload["content"]),
        cast(str, payload["summary"]),
    )
    try:
        return validate_generated_automated_refactor(request, generated)
    except ValueError as error:
        raise AutomatedRefactorError(str(error)) from error


class JsonCommandAutomatedRefactorGenerator:
    """Automated refactor generator using strict JSON stdin/stdout exchange."""

    def __init__(self, config: CommandAnalyzerConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def generate(
        self,
        request: AutomatedRefactorRequest,
    ) -> GeneratedAutomatedRefactor:
        """Exchange one refactor through an injected shell-free runner."""
        result = self._runner.run(
            self._config.command,
            json.dumps(_request_payload(request), ensure_ascii=False),
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise AutomatedRefactorError(
                f"Refactor generator failed with exit code {result.returncode}"
            )
        return _decode_refactor(result.stdout, request)


class CodexExecAutomatedRefactorGenerator:
    """Automated refactor generator using isolated ephemeral Codex exec."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        project_root: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex refactor command needs one executable")
        self._config = config
        self._runner = runner
        self._project_root = project_root.resolve()
        self._executable = (command_resolver or SystemCodexCommandResolver()).resolve(
            config.command[0]
        )

    def generate(
        self,
        request: AutomatedRefactorRequest,
    ) -> GeneratedAutomatedRefactor:
        """Exchange one refactor from a project-external temporary directory."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(
                prefix="sdd-tdd-automated-refactor-"
            ) as directory:
                exchange = Path(directory).resolve()
                if (
                    exchange == self._project_root
                    or self._project_root in exchange.parents
                ):
                    raise AutomatedRefactorError(
                        "Automated refactor workspace is not project-external"
                    )
                schema_path = exchange / "automated-refactor.schema.json"
                output_path = exchange / "automated-refactor.json"
                schema_path.write_text(
                    json.dumps(AUTOMATED_REFACTOR_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path, exchange),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise AutomatedRefactorError(
                        "Codex refactor generator failed with exit code "
                        f"{result.returncode}"
                    )
                return _decode_refactor(
                    output_path.read_text(encoding="utf-8"),
                    request,
                )
        except OSError as error:
            raise AutomatedRefactorError(
                "Codex automated refactor output could not be read"
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


def _record(
    request: AutomatedRefactorRequest,
    generated: GeneratedAutomatedRefactor,
) -> Dict[str, object]:
    return {
        "file_path": generated.file_path,
        "before_sha256": hashlib.sha256(request.source.content.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(generated.content.encode()).hexdigest(),
        "completion_sha256": request.completion_sha256,
        "review_sha256": request.review_sha256,
    }


def _write_change(
    context: _RefactorContext,
    source_path: Path,
    request: AutomatedRefactorRequest,
    generated: GeneratedAutomatedRefactor,
) -> Dict[str, object]:
    state = dict(context.state)
    record = _record(request, generated)
    state["automated_refactor"] = record
    source_temporary = source_path.with_name(f".{source_path.name}.agent-refactor.tmp")
    state_temporary = context.state_path.with_name(".state.json.automated-refactor.tmp")
    created = []
    source_replaced = False
    try:
        with source_temporary.open("x", encoding="utf-8") as stream:
            stream.write(generated.content)
        created.append(source_temporary)
        with state_temporary.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(state, indent=2)}\n")
        created.append(state_temporary)
        if (
            source_path.read_text(encoding="utf-8") != request.source.content
            or context.state_path.read_text(encoding="utf-8") != context.raw_state
        ):
            raise AutomatedRefactorError(
                "Automated refactor inputs changed concurrently"
            )
        source_temporary.replace(source_path)
        created.remove(source_temporary)
        source_replaced = True
        state_temporary.replace(context.state_path)
        created.remove(state_temporary)
    except FileExistsError as error:
        raise AutomatedRefactorError(
            "Automated refactor update is already in progress"
        ) from error
    except (OSError, UnicodeError) as error:
        if source_replaced:
            _restore(context, source_path, generated, request.source.content)
        raise AutomatedRefactorError(
            "Automated refactor could not be applied"
        ) from error
    finally:
        for temporary in created:
            if temporary.exists():
                temporary.unlink()
    return record


def _restore(
    context: _RefactorContext,
    source_path: Path,
    generated: GeneratedAutomatedRefactor,
    original_content: str,
) -> None:
    source_temporary = source_path.with_name(
        f".{source_path.name}.agent-refactor-rollback.tmp"
    )
    state_temporary = context.state_path.with_name(
        ".state.json.automated-refactor-rollback.tmp"
    )
    try:
        if source_path.read_text(encoding="utf-8") != generated.content:
            raise AutomatedRefactorError("Generated source changed before rollback")
        with source_temporary.open("x", encoding="utf-8") as stream:
            stream.write(original_content)
        with state_temporary.open("x", encoding="utf-8") as stream:
            stream.write(context.raw_state)
        source_temporary.replace(source_path)
        state_temporary.replace(context.state_path)
    except (OSError, UnicodeError) as error:
        raise AutomatedRefactorError("Automated refactor rollback failed") from error
    finally:
        for temporary in (source_temporary, state_temporary):
            if temporary.exists():
                temporary.unlink()


def apply_active_automated_refactor(
    root: Path,
    generator: AutomatedRefactorGenerator,
    runner: TestCommandRunner,
) -> AutomatedRefactorRun:
    """Generate, apply, verify, and safely roll back one source refactor."""
    try:
        status = load_project_status(root)
        if status.current_session is None:
            raise AutomatedRefactorError("Project has no active Session")
        context = _load_context(root, status.current_session)
        request = _request_from_context(root, context)
        generated = generator.generate(request)
        validate_generated_automated_refactor(request, generated)
        after_generation = _load_context(root, status.current_session)
        if after_generation.raw_state != context.raw_state:
            raise AutomatedRefactorError(
                "Automated refactor inputs changed concurrently"
            )
        source_path = _source_path(root, generated.file_path)
        record = _write_change(context, source_path, request, generated)
        try:
            complete_active_refactor(root, runner)
        except (RefactorVerificationError, RedExecutionError) as error:
            _restore(context, source_path, generated, request.source.content)
            raise AutomatedRefactorError(
                "Automated refactor verification failed"
            ) from error
        return AutomatedRefactorRun(
            status.current_session,
            generated.file_path,
            cast(str, record["before_sha256"]),
            cast(str, record["after_sha256"]),
        )
    except RefactorVerificationError as error:
        raise AutomatedRefactorError(str(error)) from error
    except ValueError as error:
        raise AutomatedRefactorError(str(error)) from error
