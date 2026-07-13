import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProjectStatus:
    """An immutable snapshot of project and active-session status."""

    project_name: str
    target_language: str
    build_tool: str
    test_frameworks: Tuple[str, ...]
    current_session: Optional[str]
    session_state: Optional[str]


def _load_generated_yaml(path: Path) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    scalars: Dict[str, str] = {}
    lists: Dict[str, List[str]] = {}
    current_list: Optional[str] = None

    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if line[0].isspace() and value.startswith("- ") and current_list:
            lists[current_list].append(value[2:].strip())
            continue

        key, separator, scalar = value.partition(":")
        if not separator:
            raise ValueError(f"Invalid project metadata line: {value}")
        current_list = None
        if scalar.strip():
            scalars[key] = scalar.strip()
        else:
            current_list = key
            lists[key] = []
    return scalars, lists


def _load_session_state(root: Path, session_id: Optional[str]) -> Optional[str]:
    if session_id is None:
        return None
    if (
        not session_id
        or session_id in {".", ".."}
        or "/" in session_id
        or "\\" in session_id
    ):
        raise ValueError(f"Invalid session identifier: {session_id}")
    state_path = root / ".agent" / "sessions" / session_id / "state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Session state must be a JSON object")
    state = payload.get("state")
    if not isinstance(state, str):
        raise ValueError("Session state must be a string")
    return state


def load_project_status(root: Path) -> ProjectStatus:
    """Load project classification and active-session status from a workspace."""
    metadata_path = root / ".agent" / "project.yml"
    scalars, lists = _load_generated_yaml(metadata_path)
    current_session = scalars.get("current_session")
    return ProjectStatus(
        project_name=scalars["name"],
        target_language=scalars.get("target_language", "unknown"),
        build_tool=scalars.get("build_tool", "unknown"),
        test_frameworks=tuple(lists.get("test_frameworks", [])),
        current_session=current_session,
        session_state=_load_session_state(root, current_session),
    )


def render_project_status(status: ProjectStatus) -> str:
    """Render a project status snapshot as deterministic plain text."""
    frameworks = ", ".join(status.test_frameworks) or "none"
    session = status.current_session or "none"
    state = status.session_state or "none"
    return (
        f"Project: {status.project_name}\n"
        f"Language: {status.target_language}\n"
        f"Build tool: {status.build_tool}\n"
        f"Test frameworks: {frameworks}\n"
        f"Session: {session}\n"
        f"State: {state}\n"
    )
