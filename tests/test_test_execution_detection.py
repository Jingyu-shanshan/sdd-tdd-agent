import json
from pathlib import Path

import pytest

from sdd_tdd_agent.test_execution import TestCommandDetectionError, detect_test_command
from sdd_tdd_agent.test_generation import TestCasePlan


def _case(
    file_path: str,
    name: str = "shouldExport",
) -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export",
        "Prove export.",
        file_path,
        name,
        (),
        "Export.",
        ("It works.",),
        (),
    )


def _node_project(
    root: Path,
    manager: str,
    framework: str,
) -> None:
    scripts = {"angular": "ng test", "jest": "jest", "vitest": "vitest"}
    dependencies = {
        "angular": {"@angular/core": "21.0.0"},
        "jest": {"jest": "30.0.0"},
        "vitest": {"vitest": "4.0.0"},
    }
    payload = {
        "name": "reports",
        "packageManager": f"{manager}@1.0.0",
        "scripts": {"test": scripts[framework]},
        "devDependencies": dependencies[framework],
    }
    (root / "package.json").write_text(json.dumps(payload), encoding="utf-8")
    if framework == "angular":
        (root / "angular.json").write_text('{"projects": {}}')


def _maven_project(root: Path) -> None:
    (root / "pom.xml").write_text(
        """\
<project>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
    </dependency>
  </dependencies>
</project>
""",
        encoding="utf-8",
    )


def test_should_plan_maven_single_junit_method_with_executable_wrapper(
    tmp_path: Path,
) -> None:
    _maven_project(tmp_path)
    wrapper = tmp_path / "mvnw"
    wrapper.write_text("#!/bin/sh\n")
    wrapper.chmod(0o755)

    plan = detect_test_command(
        tmp_path,
        _case("src/test/java/com/acme/ExportServiceTest.java"),
    )

    assert plan.ecosystem == "java"
    assert plan.build_tool == "maven"
    assert plan.test_framework == "junit5"
    assert plan.command == (
        "./mvnw",
        "-Dtest=com.acme.ExportServiceTest#shouldExport",
        "test",
    )


def test_should_plan_maven_with_non_executable_wrapper_through_sh(
    tmp_path: Path,
) -> None:
    _maven_project(tmp_path)
    (tmp_path / "mvnw").write_text("#!/bin/sh\n")

    plan = detect_test_command(
        tmp_path,
        _case("src/test/kotlin/com/acme/ExportServiceTest.kt"),
    )

    assert plan.command[0:2] == ("sh", "mvnw")
    assert plan.command[2] == "-Dtest=com.acme.ExportServiceTest#shouldExport"


def test_should_plan_gradle_single_junit_method_with_system_command(
    tmp_path: Path,
) -> None:
    (tmp_path / "build.gradle.kts").write_text(
        'dependencies { testImplementation("org.junit.jupiter:junit-jupiter") }'
    )

    plan = detect_test_command(
        tmp_path,
        _case("src/test/java/com/acme/ExportServiceTest.java"),
    )

    assert plan.build_tool == "gradle"
    assert plan.command == (
        "gradle",
        "test",
        "--tests",
        "com.acme.ExportServiceTest.shouldExport",
    )


@pytest.mark.parametrize(
    ("manager", "prefix"),
    [
        ("npm", ("npm", "test", "--")),
        ("pnpm", ("pnpm", "test", "--")),
        ("yarn", ("yarn", "run", "test")),
    ],
)
def test_should_plan_jest_exact_file_and_name_for_package_manager(
    tmp_path: Path,
    manager: str,
    prefix: tuple[str, ...],
) -> None:
    _node_project(tmp_path, manager, "jest")

    plan = detect_test_command(
        tmp_path,
        _case("tests/export.spec.ts", "should export one report"),
    )

    assert plan.ecosystem == "typescript"
    assert plan.build_tool == manager
    assert plan.test_framework == "jest"
    assert plan.command == prefix + (
        "--runInBand",
        "--runTestsByPath",
        "tests/export.spec.ts",
        "--testNamePattern",
        r"^should\ export\ one\ report$",
    )


def test_should_plan_vitest_non_watch_file_and_name(tmp_path: Path) -> None:
    _node_project(tmp_path, "pnpm", "vitest")

    plan = detect_test_command(
        tmp_path,
        _case("src/export.test.ts", "exports report"),
    )

    assert plan.test_framework == "vitest"
    assert plan.command == (
        "pnpm",
        "test",
        "--",
        "--run",
        "src/export.test.ts",
        "--testNamePattern",
        r"^exports\ report$",
    )


def test_should_plan_angular_non_watch_include_and_filter(tmp_path: Path) -> None:
    _node_project(tmp_path, "npm", "angular")

    plan = detect_test_command(
        tmp_path,
        _case("src/app/export.service.spec.ts", "exports report"),
    )

    assert plan.test_framework == "angular"
    assert plan.command == (
        "npm",
        "test",
        "--",
        "--watch=false",
        "--include=src/app/export.service.spec.ts",
        r"--filter=^exports\ report$",
    )


def test_should_escape_regular_expression_characters_in_node_test_name(
    tmp_path: Path,
) -> None:
    _node_project(tmp_path, "npm", "jest")

    plan = detect_test_command(
        tmp_path,
        _case("tests/export.spec.ts", "exports [one] report?"),
    )

    assert plan.command[-1] == r"^exports\ \[one\]\ report\?$"


def test_should_select_node_in_mixed_workspace_from_test_extension(
    tmp_path: Path,
) -> None:
    (tmp_path / "pom.xml").write_text("<project/>")
    _node_project(tmp_path, "npm", "vitest")

    plan = detect_test_command(tmp_path, _case("src/export.test.ts"))

    assert plan.ecosystem == "typescript"
    assert plan.test_framework == "vitest"


@pytest.mark.parametrize(
    ("case", "message"),
    [
        (_case("../ExportTest.java"), "safe relative"),
        (_case("test/ExportTest.java"), "standard test source"),
        (_case("src/test/java/Export-Test.java"), "class name"),
        (_case("src/test/java/ExportTest.java", "not a method"), "method name"),
        (_case("tests/export.rb"), "extension"),
        (_case("tests/export.spec.ts", "bad\x00name"), "null bytes"),
    ],
)
def test_should_reject_unsafe_or_unsupported_test_selector(
    tmp_path: Path,
    case: TestCasePlan,
    message: str,
) -> None:
    (tmp_path / "pom.xml").write_text("<project/>")

    with pytest.raises(TestCommandDetectionError, match=message):
        detect_test_command(tmp_path, case)


def test_should_reject_java_test_without_build_marker(tmp_path: Path) -> None:
    with pytest.raises(TestCommandDetectionError, match="build tool"):
        detect_test_command(
            tmp_path,
            _case("src/test/java/com/acme/ExportTest.java"),
        )
