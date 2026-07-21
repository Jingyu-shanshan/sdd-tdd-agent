from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Optional, Protocol, Tuple

from sdd_tdd_agent.production_source_generation import (
    MAX_PRODUCTION_CONTEXT_BYTES,
    MAX_PRODUCTION_SOURCE_BYTES,
    GeneratedProductionSource,
    ProductionSourceGenerationRequest,
    production_source_path,
    validate_generated_production_source,
)
from sdd_tdd_agent.tdd_cycle import SourceSnapshot


MAX_PRODUCTION_SOURCE_FILES = 200
EXCLUDED_DIRECTORY_NAMES = {
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}


class ProductionSourceWorkspaceError(RuntimeError):
    """Safe public error for production-source collection and writing."""

    __test__ = False


class ProductionSourceCollector(Protocol):
    """Typed boundary for collecting only visible production source."""

    def collect(
        self,
        root: Path,
        source_roots: Tuple[str, ...] = ("src",),
    ) -> Tuple[SourceSnapshot, ...]:
        """Collect deterministic snapshots below exact writable roots."""
        ...


@dataclass(frozen=True)
class ProductionSourceWriteResult:
    """Result of atomically writing one production source."""

    __test__: ClassVar[bool] = False

    file_path: str
    replaced_existing: bool


class ProductionSourceWriter(Protocol):
    """Typed boundary for one optimistic production-source write."""

    def write(
        self,
        root: Path,
        request: ProductionSourceGenerationRequest,
        generated: GeneratedProductionSource,
    ) -> ProductionSourceWriteResult:
        """Write one validated source without following symbolic links."""
        ...


def _read_snapshot(root: Path, path: Path) -> SourceSnapshot:
    relative = path.relative_to(root).as_posix()
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ProductionSourceWorkspaceError(
            f"Production source could not be read: {relative}"
        ) from error
    if not content.strip():
        raise ProductionSourceWorkspaceError(f"Production source is empty: {relative}")
    if len(content.encode("utf-8")) > MAX_PRODUCTION_SOURCE_BYTES:
        raise ProductionSourceWorkspaceError(
            f"Production source is too large: {relative}"
        )
    return SourceSnapshot(relative, content)


class WorkspaceProductionSourceCollector:
    """Collect bounded production source while excluding all test-like paths."""

    def collect(
        self,
        root: Path,
        source_roots: Tuple[str, ...] = ("src",),
    ) -> Tuple[SourceSnapshot, ...]:
        """Collect safe deterministic source snapshots below allowed roots."""
        project = root.resolve()
        candidates: Dict[str, Path] = {}
        for source_root_value in source_roots:
            relative_root = production_source_path(
                f"{source_root_value}/placeholder.ts",
                source_roots,
            ).parent
            source_root = project
            unsafe_root = False
            for part in relative_root.parts:
                source_root = source_root / part
                if source_root.is_symlink():
                    unsafe_root = True
                    break
            if unsafe_root or not source_root.is_dir():
                continue
            for path in source_root.rglob("*"):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(project).as_posix()
                if any(part in EXCLUDED_DIRECTORY_NAMES for part in path.parts):
                    continue
                try:
                    normalized = production_source_path(
                        relative,
                        source_roots,
                    ).as_posix()
                except ValueError:
                    continue
                candidates[normalized] = path
        if len(candidates) > MAX_PRODUCTION_SOURCE_FILES:
            raise ProductionSourceWorkspaceError(
                "Production source context contains too many files"
            )
        snapshots = tuple(
            _read_snapshot(project, candidates[path]) for path in sorted(candidates)
        )
        total = sum(len(snapshot.content.encode("utf-8")) for snapshot in snapshots)
        if total > MAX_PRODUCTION_CONTEXT_BYTES:
            raise ProductionSourceWorkspaceError(
                "Production source context is too large"
            )
        return snapshots


def _destination(
    root: Path,
    file_path: str,
    source_roots: Tuple[str, ...],
) -> Path:
    project = root.resolve()
    relative = production_source_path(file_path, source_roots)
    current = project
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ProductionSourceWorkspaceError(
                "Production source destination contains a symbolic link"
            )
    return project.joinpath(*relative.parts)


def _expected_target(
    request: ProductionSourceGenerationRequest,
    file_path: str,
) -> Optional[SourceSnapshot]:
    normalized = PurePosixPath(file_path.replace("\\", "/")).as_posix()
    for snapshot in request.context.production_sources:
        if snapshot.path.replace("\\", "/") == normalized:
            return snapshot
    return None


def _check_target(destination: Path, expected: Optional[SourceSnapshot]) -> bool:
    if destination.exists():
        if not destination.is_file() or expected is None:
            raise ProductionSourceWorkspaceError(
                "Production source target changed concurrently"
            )
        try:
            content = destination.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ProductionSourceWorkspaceError(
                "Production source target could not be verified"
            ) from error
        if content != expected.content:
            raise ProductionSourceWorkspaceError(
                "Production source target changed concurrently"
            )
        return True
    if expected is not None:
        raise ProductionSourceWorkspaceError(
            "Production source target changed concurrently"
        )
    return False


class AtomicProductionSourceWriter:
    """Atomically create or replace exactly one captured production source."""

    def write(
        self,
        root: Path,
        request: ProductionSourceGenerationRequest,
        generated: GeneratedProductionSource,
    ) -> ProductionSourceWriteResult:
        """Write one complete source after optimistic concurrency checks."""
        validate_generated_production_source(request, generated)
        destination = _destination(
            root,
            generated.file_path,
            request.production_source_roots,
        )
        expected = _expected_target(request, generated.file_path)
        replaced_existing = _check_target(destination, expected)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ProductionSourceWorkspaceError(
                "Production source destination could not be prepared"
            ) from error
        destination = _destination(
            root,
            generated.file_path,
            request.production_source_roots,
        )
        temporary = destination.with_name(f".{destination.name}.agent.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(generated.content)
            _check_target(destination, expected)
            temporary.replace(destination)
        except FileExistsError as error:
            raise ProductionSourceWorkspaceError(
                "Production source atomic temporary file already exists"
            ) from error
        except ProductionSourceWorkspaceError:
            if temporary.exists():
                temporary.unlink()
            raise
        except OSError as error:
            if temporary.exists():
                temporary.unlink()
            raise ProductionSourceWorkspaceError(
                "Production source could not be written"
            ) from error
        return ProductionSourceWriteResult(generated.file_path, replaced_existing)
