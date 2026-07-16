from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Optional, Protocol, Tuple

from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    MAX_SOURCE_BYTES,
    TestSourceGenerationRequest,
    validate_generated_test_source,
)


SOURCE_SUFFIXES = {
    ".css",
    ".gradle",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".py",
    ".scss",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
}
ROOT_MARKERS = (
    "angular.json",
    "build.gradle",
    "build.gradle.kts",
    "package.json",
    "pom.xml",
    "pnpm-lock.yaml",
    "tsconfig.json",
    "yarn.lock",
)
EXCLUDED_PARTS = {
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
MAX_SOURCE_FILES = 200
MAX_SOURCE_CONTEXT_BYTES = 2_000_000


class TestSourceWorkspaceError(RuntimeError):
    """Safe public error for source collection or generated test writes."""

    __test__ = False


class TestSourceCollector(Protocol):
    """Typed boundary for collecting explicit current project source."""

    def collect(
        self,
        root: Path,
        target_test_file: str,
    ) -> Tuple[SourceSnapshot, ...]:
        """Collect safe source snapshots for one current test."""
        ...


@dataclass(frozen=True)
class TestSourceWriteResult:
    """Result of atomically writing one generated planned test file."""

    file_path: str
    replaced_existing: bool


class TestSourceWriter(Protocol):
    """Typed boundary for writing one validated generated test source."""

    def write(
        self,
        root: Path,
        request: TestSourceGenerationRequest,
        generated: GeneratedTestSource,
    ) -> TestSourceWriteResult:
        """Write the generated source only if the captured target is current."""
        ...


def _relative_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not value.strip()
        or "\0" in value
        or path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] in {".agent", ".git"}
        or (
            len(normalized) >= 3 and normalized[0].isalpha() and normalized[1:3] == ":/"
        )
    ):
        raise TestSourceWorkspaceError("Test source path must be a safe relative path")
    return path


def _is_visible_source(path: Path, source_root: Path) -> bool:
    relative = path.relative_to(source_root)
    return (
        path.is_file()
        and not path.is_symlink()
        and path.suffix.lower() in SOURCE_SUFFIXES
        and not any(part.startswith(".") for part in relative.parts)
        and not any(part in EXCLUDED_PARTS for part in relative.parts)
    )


def _has_symlink_component(root: Path, relative: PurePosixPath) -> bool:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _read_snapshot(root: Path, path: Path) -> SourceSnapshot:
    relative = path.relative_to(root).as_posix()
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise TestSourceWorkspaceError(
            f"Visible source is not valid UTF-8: {relative}"
        ) from error
    except OSError as error:
        raise TestSourceWorkspaceError(
            f"Visible source could not be read: {relative}"
        ) from error
    if not content.strip():
        raise TestSourceWorkspaceError(f"Visible source is empty: {relative}")
    if len(content.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise TestSourceWorkspaceError(f"Visible source is too large: {relative}")
    return SourceSnapshot(relative, content)


class WorkspaceSourceCollector:
    """Collect bounded source from explicit project roots and marker files."""

    def collect(
        self,
        root: Path,
        target_test_file: str,
    ) -> Tuple[SourceSnapshot, ...]:
        """Collect deterministic UTF-8 snapshots without following symlinks."""
        project = root.resolve()
        target_relative = _relative_path(target_test_file)
        candidates: Dict[str, Path] = {}
        source_root = project / "src"
        if source_root.is_dir() and not source_root.is_symlink():
            for path in source_root.rglob("*"):
                if _is_visible_source(path, source_root):
                    candidates[path.relative_to(project).as_posix()] = path
        for marker in ROOT_MARKERS:
            path = project / marker
            if path.is_file() and not path.is_symlink():
                candidates[marker] = path
        target = project.joinpath(*target_relative.parts)
        if _has_symlink_component(project, target_relative):
            raise TestSourceWorkspaceError("Planned test source is a symbolic link")
        if target.is_file():
            candidates[target_relative.as_posix()] = target
        if len(candidates) > MAX_SOURCE_FILES:
            raise TestSourceWorkspaceError("Source context contains too many files")
        snapshots = tuple(
            _read_snapshot(project, candidates[path]) for path in sorted(candidates)
        )
        total_bytes = sum(len(item.content.encode("utf-8")) for item in snapshots)
        if total_bytes > MAX_SOURCE_CONTEXT_BYTES:
            raise TestSourceWorkspaceError("Source context is too large")
        return snapshots


def _expected_target(
    request: TestSourceGenerationRequest,
) -> Optional[SourceSnapshot]:
    target = request.current_test.test_file.replace("\\", "/")
    for snapshot in request.sources:
        if snapshot.path.replace("\\", "/") == target:
            return snapshot
    return None


def _destination(root: Path, file_path: str) -> Path:
    project = root.resolve()
    relative = _relative_path(file_path)
    current = project
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise TestSourceWorkspaceError(
                "Test source destination contains a symbolic link"
            )
    destination = project.joinpath(*relative.parts)
    if destination.is_symlink():
        raise TestSourceWorkspaceError("Test source destination is a symbolic link")
    return destination


def _check_target(destination: Path, expected: Optional[SourceSnapshot]) -> bool:
    if destination.exists():
        if not destination.is_file() or expected is None:
            raise TestSourceWorkspaceError("Test source target changed concurrently")
        try:
            current = destination.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise TestSourceWorkspaceError(
                "Test source target could not be verified"
            ) from error
        if current != expected.content:
            raise TestSourceWorkspaceError("Test source target changed concurrently")
        return True
    if expected is not None:
        raise TestSourceWorkspaceError("Test source target changed concurrently")
    return False


class AtomicTestSourceWriter:
    """Atomically write one planned test after optimistic concurrency checks."""

    def write(
        self,
        root: Path,
        request: TestSourceGenerationRequest,
        generated: GeneratedTestSource,
    ) -> TestSourceWriteResult:
        """Write one exact validated test file without following symlinks."""
        validate_generated_test_source(request, generated)
        destination = _destination(root, generated.file_path)
        expected = _expected_target(request)
        replaced_existing = _check_target(destination, expected)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise TestSourceWorkspaceError(
                "Test source destination could not be prepared"
            ) from error
        _destination(root, generated.file_path)
        temporary = destination.with_name(f".{destination.name}.agent.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(generated.content)
            _check_target(destination, expected)
            temporary.replace(destination)
        except FileExistsError as error:
            raise TestSourceWorkspaceError(
                "Test source atomic temporary file already exists"
            ) from error
        except TestSourceWorkspaceError:
            if temporary.exists():
                temporary.unlink()
            raise
        except OSError as error:
            if temporary.exists():
                temporary.unlink()
            raise TestSourceWorkspaceError(
                "Generated test source could not be written"
            ) from error
        return TestSourceWriteResult(generated.file_path, replaced_existing)
