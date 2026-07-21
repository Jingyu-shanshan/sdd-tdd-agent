import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


MAX_PROJECT_MEMORY_BYTES = 1_000_000
MEMORY_FILENAMES = ("project.yml", "architecture.md", "conventions.md")


class ProjectMemoryError(ValueError):
    """Safe error raised for invalid tracked project memory."""


@dataclass(frozen=True)
class ProjectMemory:
    """One coherent bounded snapshot of tracked project knowledge."""

    project_metadata: str
    architecture: str
    conventions: str
    digest: str


def _memory_digest(contents: Tuple[str, ...]) -> str:
    payload = json.dumps(contents, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_memory_files(workspace: Path) -> Tuple[str, ...]:
    if workspace.is_symlink():
        raise ProjectMemoryError("Project memory path is unsafe")
    contents = []
    snapshots: Dict[Path, object] = {}
    total_size = 0
    try:
        for filename in MEMORY_FILENAMES:
            path = workspace / filename
            if path.is_symlink():
                raise ProjectMemoryError("Project memory path is unsafe")
            if not path.is_file():
                raise ProjectMemoryError("Project memory file is invalid")
            before = path.stat()
            data = path.read_bytes()
            if path.stat() != before:
                raise ProjectMemoryError("Project memory changed concurrently")
            if not data:
                raise ProjectMemoryError("Project memory file is invalid")
            total_size += len(data)
            if total_size > MAX_PROJECT_MEMORY_BYTES:
                raise ProjectMemoryError("Project memory is too large")
            contents.append(data.decode("utf-8"))
            snapshots[path] = before
        if any(path.stat() != snapshot for path, snapshot in snapshots.items()):
            raise ProjectMemoryError("Project memory changed concurrently")
    except ProjectMemoryError:
        raise
    except (OSError, UnicodeError) as error:
        raise ProjectMemoryError("Project memory file is invalid") from error
    return tuple(contents)


def load_project_memory(root: Path) -> ProjectMemory:
    """Load and validate the canonical tracked project-memory snapshot."""
    contents = _read_memory_files(root / ".agent")
    return ProjectMemory(
        project_metadata=contents[0],
        architecture=contents[1],
        conventions=contents[2],
        digest=_memory_digest(contents),
    )


def render_project_memory(memory: ProjectMemory) -> str:
    """Render snapshot identity and sizes without exposing project content."""
    values = (memory.project_metadata, memory.architecture, memory.conventions)
    lines = ["Project memory: ready", f"Digest: {memory.digest}"]
    lines.extend(
        f"- {filename}: {len(value.encode('utf-8'))} bytes"
        for filename, value in zip(MEMORY_FILENAMES, values)
    )
    return "\n".join(lines) + "\n"
