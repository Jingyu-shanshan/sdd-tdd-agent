from pathlib import Path


WORKSPACE_DIRECTORIES = ("memories", "sessions", "cache", "logs", "metrics")

CONFIG = """max_iterations: 20
max_compile_failures: 5
max_test_failures: 5
max_refactor_iterations: 3
max_duration_minutes: 30
"""

ARCHITECTURE = """# Architecture

Record the project's structural decisions and constraints here.
"""

CONVENTIONS = """# Conventions

Record the project's coding and testing conventions here.
"""


def initialize_project(root: Path) -> None:
    """Create the standard agent workspace directories below a project root."""
    workspace = root / ".agent"
    workspace.mkdir(parents=True, exist_ok=True)
    for directory in WORKSPACE_DIRECTORIES:
        (workspace / directory).mkdir(exist_ok=True)

    metadata = {
        "config.yml": CONFIG,
        "project.yml": f"name: {root.name}\n",
        "architecture.md": ARCHITECTURE,
        "conventions.md": CONVENTIONS,
    }
    for filename, content in metadata.items():
        try:
            with (workspace / filename).open("x", encoding="utf-8") as file:
                file.write(content)
        except FileExistsError:
            pass
