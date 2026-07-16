import json
from dataclasses import replace
from pathlib import Path

import pytest

from sdd_tdd_agent.test_execution import detect_full_test_command
from tests.production_source_support import test_case as _test_case


def _node_project(root: Path, manager: str, framework: str) -> None:
    scripts = {"angular": "ng test", "jest": "jest", "vitest": "vitest"}
    dependencies = {
        "angular": {"@angular/core": "21.0.0"},
        "jest": {"jest": "30.0.0"},
        "vitest": {"vitest": "4.0.0"},
    }
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": f"{manager}@1.0.0",
                "scripts": {"test": scripts[framework]},
                "devDependencies": dependencies[framework],
            }
        ),
        encoding="utf-8",
    )
    if framework == "angular":
        (root / "angular.json").write_text('{"projects": {}}')


def test_should_plan_complete_maven_suite_with_wrapper(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text(
        """\
<project><dependencies><dependency>
<groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId>
</dependency></dependencies></project>
"""
    )
    wrapper = tmp_path / "mvnw"
    wrapper.write_text("#!/bin/sh\n")
    wrapper.chmod(0o755)
    case = replace(
        _test_case(),
        test_file="src/test/java/acme/ExportTest.java",
        test_name="exportsReport",
    )

    plan = detect_full_test_command(tmp_path, case)

    assert plan.ecosystem == "java"
    assert plan.command == ("./mvnw", "test")


def test_should_plan_complete_gradle_suite_without_test_filter(tmp_path: Path) -> None:
    (tmp_path / "build.gradle.kts").write_text(
        'dependencies { testImplementation("org.junit.jupiter:junit-jupiter") }'
    )
    (tmp_path / "gradlew").write_text("#!/bin/sh\n")
    case = replace(
        _test_case(),
        test_file="src/test/java/acme/ExportTest.java",
        test_name="exportsReport",
    )

    plan = detect_full_test_command(tmp_path, case)

    assert plan.command == ("sh", "gradlew", "test")
    assert "--tests" not in plan.command


@pytest.mark.parametrize(
    ("manager", "framework", "expected"),
    [
        ("npm", "jest", ("npm", "test", "--", "--runInBand")),
        ("pnpm", "vitest", ("pnpm", "test", "--", "--run")),
        ("yarn", "vitest", ("yarn", "run", "test", "--run")),
        ("npm", "angular", ("npm", "test", "--", "--watch=false")),
    ],
)
def test_should_plan_complete_node_suite_without_file_or_name_filter(
    tmp_path: Path,
    manager: str,
    framework: str,
    expected: tuple[str, ...],
) -> None:
    _node_project(tmp_path, manager, framework)

    plan = detect_full_test_command(tmp_path, _test_case())

    assert plan.command == expected
    assert "src/export.test.ts" not in plan.command
    assert all("testNamePattern" not in token for token in plan.command)
