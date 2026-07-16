from pathlib import Path
from typing import Optional

from sdd_tdd_agent.project_detection import ProjectProfile, detect_project


WORKSPACE_DIRECTORIES = ("memories", "sessions", "cache", "logs", "metrics")

CONFIG = """max_iterations: 20
max_compile_failures: 5
max_test_failures: 5
max_refactor_iterations: 3
max_duration_minutes: 30
test_command_timeout_seconds: 300
full_test_suite_timeout_seconds: 900
"""

ARCHITECTURE = """# Architecture

Record the project's structural decisions and constraints here.
"""

CONVENTIONS = """# Conventions

Record the project's coding and testing conventions here.
"""


def _render_project_metadata(root: Path, profile: Optional[ProjectProfile]) -> str:
    metadata = f"name: {root.name}\n"
    if profile is None:
        return metadata

    metadata += (
        f"target_language: {profile.target_language}\n"
        f"build_tool: {profile.build_tool}\n"
    )
    if profile.test_frameworks:
        metadata += "test_frameworks:\n"
        metadata += "".join(
            f"  - {framework}\n" for framework in profile.test_frameworks
        )
    return metadata


def _write_once(path: Path, content: str) -> None:
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(content)
    except FileExistsError:
        return


def initialize_project(root: Path) -> None:
    """Create the standard agent workspace directories below a project root."""
    workspace = root / ".agent"
    workspace.mkdir(parents=True, exist_ok=True)
    for directory in WORKSPACE_DIRECTORIES:
        (workspace / directory).mkdir(exist_ok=True)

    profile = detect_project(root)
    metadata = {
        "config.yml": CONFIG,
        "project.yml": _render_project_metadata(root, profile),
        "architecture.md": ARCHITECTURE,
        "conventions.md": CONVENTIONS,
    }
    for filename, content in metadata.items():
        _write_once(workspace / filename, content)
