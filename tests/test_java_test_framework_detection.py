from pathlib import Path

from sdd_tdd_agent.project_detection import detect_project
from sdd_tdd_agent.project_init import initialize_project


def test_should_detect_junit5_dependency(tmp_path: Path) -> None:
    pom = """\
<project>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
    </dependency>
  </dependencies>
</project>
"""
    (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.test_frameworks == ("junit5",)


def test_should_detect_junit5_in_standard_maven_namespace(tmp_path: Path) -> None:
    pom = """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter-api</artifactId>
    </dependency>
  </dependencies>
</project>
"""
    (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.test_frameworks == ("junit5",)


def test_should_persist_detected_test_framework(tmp_path: Path) -> None:
    pom = """\
<project>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter-engine</artifactId>
    </dependency>
  </dependencies>
</project>
"""
    (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

    initialize_project(tmp_path)

    metadata = (tmp_path / ".agent" / "project.yml").read_text(encoding="utf-8")
    assert "test_frameworks:\n  - junit5\n" in metadata


def test_should_not_classify_non_jupiter_dependency(tmp_path: Path) -> None:
    pom = """\
<project>
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
    </dependency>
  </dependencies>
</project>
"""
    (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

    profile = detect_project(tmp_path)

    assert profile is not None
    assert profile.test_frameworks == ()
