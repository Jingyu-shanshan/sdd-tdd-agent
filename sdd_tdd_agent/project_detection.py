import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from xml.etree import ElementTree

from sdd_tdd_agent.node_project import load_node_project


GRADLE_BUILD_FILES = ("build.gradle", "build.gradle.kts")
MAVEN_QUALITY_PLUGINS = (
    (("org.apache.maven.plugins", "maven-checkstyle-plugin"), "checkstyle"),
    (("com.github.spotbugs", "spotbugs-maven-plugin"), "spotbugs"),
    (("org.apache.maven.plugins", "maven-pmd-plugin"), "pmd"),
)
GRADLE_QUALITY_PLUGINS = (
    ("checkstyle", "checkstyle"),
    ("com.github.spotbugs", "spotbugs"),
    ("pmd", "pmd"),
)


@dataclass(frozen=True)
class ProjectProfile:
    """A detected target language and its build tool."""

    target_language: str
    build_tool: str
    test_frameworks: Tuple[str, ...] = ()
    quality_tools: Tuple[str, ...] = ()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ElementTree.Element, name: str) -> Optional[str]:
    for child in element:
        if _local_name(child.tag) == name:
            return child.text
    return None


def _detect_maven_features(
    pom_path: Path,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if pom_path.stat().st_size == 0:
        return (), ()

    root = ElementTree.parse(pom_path).getroot()
    has_junit = False
    plugins = set()
    for element in root.iter():
        kind = _local_name(element.tag)
        group_id = _child_text(element, "groupId")
        artifact_id = _child_text(element, "artifactId")
        if kind == "dependency" and (
            group_id == "org.junit.jupiter"
            and artifact_id is not None
            and artifact_id.startswith("junit-jupiter")
        ):
            has_junit = True
        if kind == "plugin" and artifact_id is not None:
            plugins.add((group_id or "org.apache.maven.plugins", artifact_id))
    frameworks = ("junit5",) if has_junit else ()
    quality = tuple(
        tool for coordinates, tool in MAVEN_QUALITY_PLUGINS if coordinates in plugins
    )
    return frameworks, quality


def _has_gradle_plugin(content: str, plugin: str) -> bool:
    quoted = re.escape(plugin)
    pattern = (
        rf"(?m)^\s*(?:{quoted}|id\s*(?:\(\s*)?[\"']{quoted}[\"']\s*\)?"
        rf"(?:\s+version\s+[\"'][^\"']+[\"'])?)\s*$"
    )
    return re.search(pattern, content) is not None


def _without_gradle_comments(content: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\r\n]*", "", content, flags=re.DOTALL)


def _detect_gradle_features(
    root: Path,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    for marker in GRADLE_BUILD_FILES:
        path = root / marker
        if not path.is_file():
            continue
        content = _without_gradle_comments(path.read_text(encoding="utf-8"))
        frameworks = ("junit5",) if "org.junit.jupiter" in content else ()
        quality = tuple(
            tool
            for plugin, tool in GRADLE_QUALITY_PLUGINS
            if _has_gradle_plugin(content, plugin)
        )
        return frameworks, quality
    return (), ()


def detect_project(root: Path) -> Optional[ProjectProfile]:
    """Detect a supported project from root-level marker files."""
    pom_path = root / "pom.xml"
    if pom_path.is_file():
        frameworks, quality = _detect_maven_features(pom_path)
        return ProjectProfile(
            target_language="java",
            build_tool="maven",
            test_frameworks=frameworks,
            quality_tools=quality,
        )
    if any((root / marker).is_file() for marker in GRADLE_BUILD_FILES):
        frameworks, quality = _detect_gradle_features(root)
        return ProjectProfile(
            target_language="java",
            build_tool="gradle",
            test_frameworks=frameworks,
            quality_tools=quality,
        )
    if (root / "package.json").is_file():
        node = load_node_project(root)
        return ProjectProfile(
            target_language="typescript",
            build_tool=node.package_manager,
            test_frameworks=(node.test_framework,),
            quality_tools=node.quality_tools,
        )
    return None
