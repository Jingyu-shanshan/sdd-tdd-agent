from dataclasses import dataclass
from pathlib import Path
from typing import Optional


GRADLE_BUILD_FILES = ("build.gradle", "build.gradle.kts")


@dataclass(frozen=True)
class ProjectProfile:
    """A detected target language and its build tool."""

    target_language: str
    build_tool: str


def detect_project(root: Path) -> Optional[ProjectProfile]:
    """Detect a supported project from root-level marker files."""
    if (root / "pom.xml").is_file():
        return ProjectProfile(target_language="java", build_tool="maven")
    if any((root / marker).is_file() for marker in GRADLE_BUILD_FILES):
        return ProjectProfile(target_language="java", build_tool="gradle")
    return None
