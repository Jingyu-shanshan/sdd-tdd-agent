import json
from pathlib import Path

import pytest

from sdd_tdd_agent.project_detection import detect_project
from sdd_tdd_agent.project_init import initialize_project


MAVEN_PROJECT = """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-pmd-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>com.github.spotbugs</groupId>
        <artifactId>spotbugs-maven-plugin</artifactId>
      </plugin>
      <plugin>
        <artifactId>maven-checkstyle-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
"""


def test_should_detect_exact_maven_quality_plugins_in_canonical_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "pom.xml").write_text(MAVEN_PROJECT, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.test_frameworks == ("junit5",)
    assert profile.quality_tools == ("checkstyle", "spotbugs", "pmd")


@pytest.mark.parametrize(
    ("marker", "content"),
    [
        (
            "build.gradle.kts",
            """\
plugins {
    java
    pmd
    id("com.github.spotbugs") version "6.0.0"
    checkstyle
}
""",
        ),
        (
            "build.gradle",
            """\
plugins {
    id 'java'
    id 'pmd'
    id 'com.github.spotbugs' version '6.0.0'
    id 'checkstyle'
}
""",
        ),
    ],
)
def test_should_detect_gradle_quality_plugins(
    tmp_path: Path,
    marker: str,
    content: str,
) -> None:
    (tmp_path / marker).write_text(content, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.quality_tools == ("checkstyle", "spotbugs", "pmd")


def test_should_ignore_gradle_plugins_inside_comments(tmp_path: Path) -> None:
    (tmp_path / "build.gradle.kts").write_text(
        """\
plugins {
    java
    /*
    checkstyle
    id("com.github.spotbugs")
    */
    // pmd
}
""",
        encoding="utf-8",
    )

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.quality_tools == ()


def _write_node_project(
    root: Path,
    scripts: dict[str, str],
    dependencies: dict[str, str],
) -> None:
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "web",
                "packageManager": "npm@11.0.0",
                "scripts": scripts,
                "devDependencies": dependencies,
            }
        ),
        encoding="utf-8",
    )


def test_should_detect_configured_node_quality_tools(tmp_path: Path) -> None:
    _write_node_project(
        tmp_path,
        {
            "test": "vitest",
            "format": "prettier --check .",
            "lint": "eslint src",
        },
        {"vitest": "4", "eslint": "9", "prettier": "3"},
    )

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.quality_tools == ("eslint", "prettier")


@pytest.mark.parametrize(
    ("scripts", "dependencies"),
    [
        (
            {"test": "vitest"},
            {"vitest": "4", "eslint": "9", "prettier": "3"},
        ),
        (
            {
                "test": "vitest",
                "lint": "eslint src",
                "format": "prettier --check .",
            },
            {"vitest": "4"},
        ),
        (
            {"test": "vitest", "lint": "myeslint src"},
            {"vitest": "4", "eslint": "9"},
        ),
    ],
)
def test_should_not_infer_node_quality_tools_from_partial_evidence(
    tmp_path: Path,
    scripts: dict[str, str],
    dependencies: dict[str, str],
) -> None:
    _write_node_project(tmp_path, scripts, dependencies)

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.quality_tools == ()


def test_should_persist_detected_quality_tools(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text(MAVEN_PROJECT, encoding="utf-8")

    initialize_project(tmp_path)

    metadata = (tmp_path / ".agent" / "project.yml").read_text(encoding="utf-8")
    assert ("quality_tools:\n  - checkstyle\n  - spotbugs\n  - pmd\n") in metadata


def test_should_omit_empty_quality_tools_from_metadata(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text("<project />", encoding="utf-8")

    initialize_project(tmp_path)

    metadata = (tmp_path / ".agent" / "project.yml").read_text(encoding="utf-8")
    assert "quality_tools:" not in metadata
