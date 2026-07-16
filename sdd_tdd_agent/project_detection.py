from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from xml.etree import ElementTree

from sdd_tdd_agent.node_project import load_node_project


GRADLE_BUILD_FILES = ("build.gradle", "build.gradle.kts")


@dataclass(frozen=True)
class ProjectProfile:
    """A detected target language and its build tool."""

    target_language: str
    build_tool: str
    test_frameworks: Tuple[str, ...] = ()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ElementTree.Element, name: str) -> Optional[str]:
    for child in element:
        if _local_name(child.tag) == name:
            return child.text
    return None


def _detect_maven_test_frameworks(pom_path: Path) -> Tuple[str, ...]:
    if pom_path.stat().st_size == 0:
        return ()

    root = ElementTree.parse(pom_path).getroot()
    for dependency in root.iter():
        if _local_name(dependency.tag) != "dependency":
            continue
        group_id = _child_text(dependency, "groupId")
        artifact_id = _child_text(dependency, "artifactId")
        if (
            group_id == "org.junit.jupiter"
            and artifact_id is not None
            and artifact_id.startswith("junit-jupiter")
        ):
            return ("junit5",)
    return ()


def _detect_gradle_test_frameworks(root: Path) -> Tuple[str, ...]:
    for marker in GRADLE_BUILD_FILES:
        path = root / marker
        if not path.is_file():
            continue
        if "org.junit.jupiter" in path.read_text(encoding="utf-8"):
            return ("junit5",)
    return ()


def detect_project(root: Path) -> Optional[ProjectProfile]:
    """Detect a supported project from root-level marker files."""
    pom_path = root / "pom.xml"
    if pom_path.is_file():
        return ProjectProfile(
            target_language="java",
            build_tool="maven",
            test_frameworks=_detect_maven_test_frameworks(pom_path),
        )
    if any((root / marker).is_file() for marker in GRADLE_BUILD_FILES):
        return ProjectProfile(
            target_language="java",
            build_tool="gradle",
            test_frameworks=_detect_gradle_test_frameworks(root),
        )
    if (root / "package.json").is_file():
        node = load_node_project(root)
        return ProjectProfile(
            target_language="typescript",
            build_tool=node.package_manager,
            test_frameworks=(node.test_framework,),
        )
    return None
