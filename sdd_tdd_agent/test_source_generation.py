from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Protocol, Set, Tuple

from sdd_tdd_agent.tdd_cycle import (
    SourceSnapshot,
    load_current_test_case,
)
from sdd_tdd_agent.test_generation import TestCasePlan


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent
    / "prompts"
    / "test_source_generation"
    / f"{PROMPT_VERSION}.md"
)
REQUIREMENT_HEADING = "# Requirement Analysis"
DESIGN_HEADING = "# Design Proposal"
MAX_SOURCE_BYTES = 1_000_000
PROTECTED_ROOTS = {".agent", ".git"}


@dataclass(frozen=True)
class TestSourceGenerationRequest:
    """Isolated typed context for authoring exactly one current test."""

    __test__: ClassVar[bool] = False

    prompt_version: str
    prompt: str
    requirement: str
    design: str
    current_test: TestCasePlan
    sources: Tuple[SourceSnapshot, ...]


@dataclass(frozen=True)
class GeneratedTestSource:
    """One complete generated test file bound to the current planned test."""

    __test__: ClassVar[bool] = False

    test_id: str
    file_path: str
    content: str


class TestSourceGenerator(Protocol):
    """Injectable model boundary for generating one complete test file."""

    def generate(self, request: TestSourceGenerationRequest) -> GeneratedTestSource:
        """Generate one test source without mutating the project."""
        ...


def _safe_relative_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ValueError("Source snapshot path must be a safe relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] in PROTECTED_ROOTS
        or (
            len(normalized) >= 3 and normalized[0].isalpha() and normalized[1:3] == ":/"
        )
    ):
        if path.parts and path.parts[0] in PROTECTED_ROOTS:
            raise ValueError("Source snapshot path references a protected root")
        raise ValueError("Source snapshot path must be a safe relative path")
    return path


def _validate_sources(value: object) -> Tuple[SourceSnapshot, ...]:
    if not isinstance(value, tuple):
        raise ValueError("Source snapshots must be a tuple")
    paths: Set[str] = set()
    for snapshot in value:
        if not isinstance(snapshot, SourceSnapshot):
            raise ValueError("Source snapshots must contain SourceSnapshot values")
        path = _safe_relative_path(snapshot.path)
        normalized = path.as_posix()
        if normalized in paths:
            raise ValueError("Source snapshots contain a duplicate path")
        if not isinstance(snapshot.content, str) or not snapshot.content.strip():
            raise ValueError("Source snapshot content must not be empty")
        if "\0" in snapshot.content:
            raise ValueError("Source snapshot content must not contain null bytes")
        if len(snapshot.content.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ValueError("Source snapshot content is too large")
        paths.add(normalized)
    return value


def _read_specification(path: Path, heading: str, subject: str) -> str:
    content = path.read_text(encoding="utf-8")
    if not content.strip() or not content.lstrip().startswith(heading):
        raise ValueError(f"Test source generation requires an approved {subject}")
    return content


def load_test_source_generation_request(
    root: Path,
    session_id: str,
    sources: Tuple[SourceSnapshot, ...],
) -> TestSourceGenerationRequest:
    """Load one isolated test-author request without mutating the project."""
    current_test = load_current_test_case(root, session_id, "WRITE_TEST")
    session = root / ".agent" / "sessions" / session_id
    requirement = _read_specification(
        session / "requirement.md",
        REQUIREMENT_HEADING,
        "requirement",
    )
    design = _read_specification(
        session / "design.md",
        DESIGN_HEADING,
        "design",
    )
    return TestSourceGenerationRequest(
        prompt_version=PROMPT_VERSION,
        prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        requirement=requirement,
        design=design,
        current_test=current_test,
        sources=_validate_sources(sources),
    )


def validate_generated_test_source(
    request: TestSourceGenerationRequest,
    generated: GeneratedTestSource,
) -> GeneratedTestSource:
    """Validate generated source is limited to the current planned test file."""
    if not isinstance(generated, GeneratedTestSource):
        raise ValueError("Test source result must be a GeneratedTestSource")
    if generated.test_id != request.current_test.test_id:
        raise ValueError("Generated test identifier does not match current test")
    if generated.file_path != request.current_test.test_file:
        raise ValueError("Generated test file path does not match current test")
    _safe_relative_path(generated.file_path)
    if not isinstance(generated.content, str) or not generated.content.strip():
        raise ValueError("Generated test source must not be empty")
    if "\0" in generated.content:
        raise ValueError("Generated test source must not contain null bytes")
    if len(generated.content.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("Generated test source is too large")
    return generated
