import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Optional, Protocol, Set, Tuple

from sdd_tdd_agent.angular_workspace import load_angular_workspace

from sdd_tdd_agent.red_execution import (
    MAX_EVIDENCE_STREAM_CHARACTERS,
    RedExecutionError,
    sanitize_test_evidence,
    validate_current_test_source_artifact,
)
from sdd_tdd_agent.tdd_cycle import (
    BlindDevelopmentContext,
    SourceSnapshot,
    load_current_test_case,
)
from sdd_tdd_agent.test_generation import TestCasePlan


PROMPT_VERSION = "v1"
ANGULAR_PROMPT_VERSION = "v2-angular"
PROMPT_DIRECTORY = Path(__file__).parent / "prompts" / "production_source_generation"
MAX_PRODUCTION_SOURCE_BYTES = 1_000_000
MAX_PRODUCTION_CONTEXT_BYTES = 2_000_000
PRODUCTION_SOURCE_SUFFIXES = {
    ".css",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".py",
    ".scss",
    ".ts",
    ".tsx",
}
TEST_DIRECTORY_NAMES = {"__tests__", "test", "tests"}
RED_EVIDENCE_FIELDS = {
    "test_id",
    "file_path",
    "command",
    "returncode",
    "stdout",
    "stderr",
}


@dataclass(frozen=True)
class ProductionSourceGenerationRequest:
    """Versioned Blind context for one minimal production-source change."""

    __test__: ClassVar[bool] = False

    prompt_version: str
    prompt: str
    context: BlindDevelopmentContext
    production_source_roots: Tuple[str, ...] = ("src",)


@dataclass(frozen=True)
class GeneratedProductionSource:
    """One complete production source generated for the current test."""

    __test__: ClassVar[bool] = False

    test_id: str
    file_path: str
    content: str


class ProductionSourceGenerator(Protocol):
    """Typed model boundary for one Blind production-source change."""

    def generate(
        self,
        request: ProductionSourceGenerationRequest,
    ) -> GeneratedProductionSource:
        """Generate exactly one complete production source file."""
        ...


def _production_source_roots(values: object) -> Tuple[PurePosixPath, ...]:
    if not isinstance(values, tuple) or not values:
        raise ValueError("Production source roots are invalid")
    roots = tuple(PurePosixPath(value) for value in values if isinstance(value, str))
    if len(roots) != len(values) or any(
        not root.parts
        or root.is_absolute()
        or ".." in root.parts
        or "\\" in value
        or value != root.as_posix()
        or any(part.startswith(".") for part in root.parts)
        for value, root in zip(values, roots)
    ):
        raise ValueError("Production source roots are invalid")
    if len(set(roots)) != len(roots):
        raise ValueError("Production source roots are invalid")
    return roots


def production_source_path(
    value: object,
    source_roots: Tuple[str, ...] = ("src",),
) -> PurePosixPath:
    """Validate and normalize one writable production-source path."""
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ValueError("Generated production source path is invalid")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    folded_parts = tuple(part.casefold() for part in path.parts)
    stem = path.stem
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or ".." in path.parts
        or any(part.startswith(".") for part in path.parts)
        or any(part in TEST_DIRECTORY_NAMES for part in folded_parts)
        or path.suffix.lower() not in PRODUCTION_SOURCE_SUFFIXES
        or stem.casefold().endswith((".test", ".spec"))
        or stem.startswith("test_")
        or stem.endswith("Test")
        or (
            len(normalized) >= 3 and normalized[0].isalpha() and normalized[1:3] == ":/"
        )
    ):
        raise ValueError("Generated production source path is invalid")
    roots = _production_source_roots(source_roots)
    if not any(
        len(path.parts) > len(root.parts)
        and path.parts[: len(root.parts)] == root.parts
        for root in roots
    ):
        raise ValueError("Generated production source path is invalid")
    return path


def load_production_source_roots(
    root: Path,
    session_id: str,
    expected_phase: str,
) -> Tuple[str, ...]:
    """Resolve the exact writable root for the current typed test case."""
    current = load_current_test_case(root, session_id, expected_phase)
    return production_source_roots_for_case(root, current)


def production_source_roots_for_case(
    root: Path,
    current: TestCasePlan,
) -> Tuple[str, ...]:
    """Resolve an exact production root from one validated test case."""
    if current.angular is None:
        return ("src",)
    workspace = load_angular_workspace(root)
    for project in workspace.projects:
        if project.name == current.angular.project:
            return (project.source_root,)
    raise ValueError("Current Angular test project is not configured")


def _load_state(root: Path, session_id: str) -> Dict[str, object]:
    path = root / ".agent" / "sessions" / session_id / "state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Blind development state could not be read") from error
    if not isinstance(value, dict):
        raise ValueError("Blind development state must be a JSON object")
    return value


def _red_stream(root: Path, value: object) -> str:
    if not isinstance(value, str) or len(value) > MAX_EVIDENCE_STREAM_CHARACTERS:
        raise ValueError("RED evidence stream is invalid")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("RED evidence stream must be valid UTF-8") from error
    if sanitize_test_evidence(root, value) != value:
        raise ValueError("RED evidence must already be sanitized")
    return value


def _load_red_outputs(
    root: Path,
    session_id: str,
    test_id: str,
    file_path: str,
) -> Tuple[str, str]:
    evidence = _load_state(root, session_id).get("red_evidence")
    if not isinstance(evidence, dict) or set(evidence) != RED_EVIDENCE_FIELDS:
        raise ValueError("RED evidence is invalid")
    command = evidence["command"]
    returncode = evidence["returncode"]
    if (
        evidence["test_id"] != test_id
        or evidence["file_path"] != file_path
        or not isinstance(command, list)
        or not command
        or any(
            not isinstance(item, str) or not item.strip() or "\0" in item
            for item in command
        )
        or isinstance(returncode, bool)
        or not isinstance(returncode, int)
        or returncode <= 0
    ):
        raise ValueError("RED evidence is invalid")
    return (
        _red_stream(root, evidence["stderr"]),
        _red_stream(root, evidence["stdout"]),
    )


def _test_source(root: Path, session_id: str, file_path: str) -> SourceSnapshot:
    try:
        before = validate_current_test_source_artifact(root, session_id, "RED")
        path = root.resolve().joinpath(*PurePosixPath(file_path).parts)
        content = path.read_text(encoding="utf-8")
        after = validate_current_test_source_artifact(root, session_id, "RED")
    except (OSError, UnicodeError, RedExecutionError) as error:
        raise ValueError(str(error)) from error
    if before != after or not content.strip():
        raise ValueError("Current test source changed during Blind context loading")
    if len(content.encode("utf-8")) > MAX_PRODUCTION_SOURCE_BYTES:
        raise ValueError("Current test source is too large")
    return SourceSnapshot(file_path, content)


def _validate_production_sources(
    sources: Tuple[SourceSnapshot, ...],
    source_roots: Tuple[str, ...],
) -> Tuple[SourceSnapshot, ...]:
    if not isinstance(sources, tuple):
        raise ValueError("Production source snapshots must be a tuple")
    paths: Set[str] = set()
    total_bytes = 0
    for snapshot in sources:
        if not isinstance(snapshot, SourceSnapshot):
            raise ValueError("Production source snapshots are invalid")
        path = production_source_path(snapshot.path, source_roots).as_posix()
        if path in paths or not snapshot.content.strip() or "\0" in snapshot.content:
            raise ValueError("Production source snapshots are invalid")
        size = len(snapshot.content.encode("utf-8"))
        if size > MAX_PRODUCTION_SOURCE_BYTES:
            raise ValueError("Production source snapshot is too large")
        total_bytes += size
        paths.add(path)
    if total_bytes > MAX_PRODUCTION_CONTEXT_BYTES:
        raise ValueError("Production source context is too large")
    return sources


def load_production_source_generation_request(
    root: Path,
    session_id: str,
    production_sources: Tuple[SourceSnapshot, ...],
    production_source_roots: Optional[Tuple[str, ...]] = None,
) -> ProductionSourceGenerationRequest:
    """Load one isolated Blind request from a trustworthy RED cycle."""
    current = load_current_test_case(root, session_id, "RED")
    resolved_roots = load_production_source_roots(root, session_id, "RED")
    if (
        production_source_roots is not None
        and production_source_roots != resolved_roots
    ):
        raise ValueError("Production source roots do not match current test")
    current_source = _test_source(root, session_id, current.test_file)
    compile_output, test_output = _load_red_outputs(
        root,
        session_id,
        current.test_id,
        current.test_file,
    )
    validate_current_test_source_artifact(root, session_id, "RED")
    context = BlindDevelopmentContext(
        current_test=current,
        production_sources=_validate_production_sources(
            production_sources,
            resolved_roots,
        ),
        compile_output=compile_output,
        test_output=test_output,
        current_test_source=current_source,
    )
    prompt_version = (
        ANGULAR_PROMPT_VERSION if current.angular is not None else PROMPT_VERSION
    )
    prompt_path = PROMPT_DIRECTORY / f"{prompt_version}.md"
    return ProductionSourceGenerationRequest(
        prompt_version,
        prompt_path.read_text(encoding="utf-8"),
        context,
        resolved_roots,
    )


def validate_generated_production_source(
    request: ProductionSourceGenerationRequest,
    generated: GeneratedProductionSource,
) -> GeneratedProductionSource:
    """Validate one exact minimal production-source result."""
    if not isinstance(request, ProductionSourceGenerationRequest):
        raise ValueError("Production source request is invalid")
    if not isinstance(generated, GeneratedProductionSource):
        raise ValueError("Production source result is invalid")
    if generated.test_id != request.context.current_test.test_id:
        raise ValueError("Generated production source test identifier is invalid")
    normalized = production_source_path(
        generated.file_path,
        request.production_source_roots,
    ).as_posix()
    if generated.file_path != normalized:
        raise ValueError("Generated production source path must be normalized")
    if not isinstance(generated.content, str) or not generated.content.strip():
        raise ValueError("Generated production source content is empty")
    if "\0" in generated.content:
        raise ValueError("Generated production source contains a null byte")
    try:
        size = len(generated.content.encode("utf-8"))
    except UnicodeError as error:
        raise ValueError("Generated production source must be valid UTF-8") from error
    if size > MAX_PRODUCTION_SOURCE_BYTES:
        raise ValueError("Generated production source is too large")
    return generated
