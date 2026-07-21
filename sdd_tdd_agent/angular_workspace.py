import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple


PROJECT_TYPES = {"application", "library"}
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class AngularWorkspaceError(ValueError):
    """Safe public error raised for invalid Angular workspace metadata."""


@dataclass(frozen=True)
class AngularProject:
    """One configured Angular application or library boundary."""

    name: str
    project_type: str
    root: str
    source_root: str
    prefix: Optional[str]


@dataclass(frozen=True)
class AngularWorkspace:
    """Strict immutable Angular workspace context used by SDD generation."""

    version: int
    projects: Tuple[AngularProject, ...]


def _strict_object(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AngularWorkspaceError(f"angular.json contains duplicate key: {key}")
        result[key] = value
    return result


def _load_document(path: Path) -> Dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except json.JSONDecodeError as error:
        raise AngularWorkspaceError("angular.json contains invalid JSON") from error
    except OSError as error:
        raise AngularWorkspaceError("angular.json could not be read") from error
    if not isinstance(value, dict):
        raise AngularWorkspaceError("angular.json must contain a JSON object")
    return value


def _safe_path(value: object, *, allow_empty: bool) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise AngularWorkspaceError("Angular project path must be a safe relative path")
    if allow_empty and not value:
        return ""
    path = PurePosixPath(value)
    if (
        value != path.as_posix()
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise AngularWorkspaceError("Angular project path must be a safe relative path")
    return value


def _project(name: object, value: object) -> AngularProject:
    if not isinstance(name, str) or NAME_PATTERN.fullmatch(name) is None:
        raise AngularWorkspaceError("Angular project name is invalid")
    if not isinstance(value, dict):
        raise AngularWorkspaceError("Angular project must be a JSON object")
    project_type = value.get("projectType")
    if project_type not in PROJECT_TYPES:
        raise AngularWorkspaceError("Angular project type is unsupported")
    root = _safe_path(value.get("root"), allow_empty=True)
    source_root = _safe_path(value.get("sourceRoot"), allow_empty=False)
    root_parts = PurePosixPath(root).parts
    if PurePosixPath(source_root).parts[: len(root_parts)] != root_parts:
        raise AngularWorkspaceError("Angular source root must be within project root")
    prefix = value.get("prefix")
    if prefix is not None and (
        not isinstance(prefix, str) or NAME_PATTERN.fullmatch(prefix) is None
    ):
        raise AngularWorkspaceError("Angular project prefix is invalid")
    return AngularProject(name, project_type, root, source_root, prefix)


def load_angular_workspace(root: Path) -> AngularWorkspace:
    """Load a root Angular workspace without resolving builders or source."""
    payload = _load_document(root / "angular.json")
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise AngularWorkspaceError("Angular workspace version must be positive")
    projects = payload.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise AngularWorkspaceError("Angular workspace requires at least one project")
    return AngularWorkspace(
        version=version,
        projects=tuple(_project(name, value) for name, value in projects.items()),
    )
