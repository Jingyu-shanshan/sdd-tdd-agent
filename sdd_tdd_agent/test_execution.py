import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Tuple

from sdd_tdd_agent.node_project import load_node_project
from sdd_tdd_agent.project_detection import GRADLE_BUILD_FILES, detect_project
from sdd_tdd_agent.test_generation import TestCasePlan


JAVA_TEST_SUFFIXES = {".java", ".kt"}
NODE_TEST_SUFFIXES = {".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"}
JAVA_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


class TestCommandDetectionError(ValueError):
    """Safe public error raised when one-test execution cannot be planned."""

    __test__ = False


@dataclass(frozen=True)
class TestCommandPlan:
    """One shell-free command plan for executing exactly one current test."""

    __test__: ClassVar[bool] = False

    ecosystem: str
    build_tool: str
    test_framework: str
    test_file: str
    test_name: str
    command: Tuple[str, ...]


def _test_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise TestCommandDetectionError("Test file must be a safe relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] in {".agent", ".git"}
        or (
            len(normalized) >= 3 and normalized[0].isalpha() and normalized[1:3] == ":/"
        )
    ):
        raise TestCommandDetectionError("Test file must be a safe relative path")
    return path


def _test_name(value: object, java: bool) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TestCommandDetectionError("Test name must not be empty")
    if "\0" in value:
        raise TestCommandDetectionError("Test name must not contain null bytes")
    if len(value) > 200:
        raise TestCommandDetectionError("Test name is too long")
    if java and JAVA_IDENTIFIER.fullmatch(value) is None:
        raise TestCommandDetectionError("Java test method name is invalid")
    return value


def _java_class(path: PurePosixPath) -> str:
    if len(path.parts) < 4 or path.parts[0:3] not in {
        ("src", "test", "java"),
        ("src", "test", "kotlin"),
    }:
        raise TestCommandDetectionError(
            "Java test file must use a standard test source root"
        )
    parts = (*path.parts[3:-1], path.stem)
    if any(JAVA_IDENTIFIER.fullmatch(part) is None for part in parts):
        raise TestCommandDetectionError("Java test class name is invalid")
    return ".".join(parts)


def _wrapper(root: Path, name: str, fallback: str) -> Tuple[str, ...]:
    path = root / name
    if not path.is_file():
        return (fallback,)
    if os.access(path, os.X_OK):
        return (f"./{name}",)
    return ("sh", name)


def _java_plan(
    root: Path,
    case: TestCasePlan,
    path: PurePosixPath,
    name: str,
) -> TestCommandPlan:
    has_maven = (root / "pom.xml").is_file()
    has_gradle = any((root / marker).is_file() for marker in GRADLE_BUILD_FILES)
    if has_maven and has_gradle:
        raise TestCommandDetectionError("Java project has multiple build tools")
    if not has_maven and not has_gradle:
        raise TestCommandDetectionError("Java build tool could not be detected")
    class_name = _java_class(path)
    profile = detect_project(root)
    if profile is None or "junit5" not in profile.test_frameworks:
        raise TestCommandDetectionError("JUnit 5 could not be verified")
    if has_maven:
        launcher = _wrapper(root, "mvnw", "mvn")
        command = launcher + (f"-Dtest={class_name}#{name}", "test")
        build_tool = "maven"
    else:
        launcher = _wrapper(root, "gradlew", "gradle")
        command = launcher + ("test", "--tests", f"{class_name}.{name}")
        build_tool = "gradle"
    return TestCommandPlan(
        "java",
        build_tool,
        "junit5",
        case.test_file,
        name,
        command,
    )


def _script_prefix(manager: str) -> Tuple[str, ...]:
    if manager == "npm":
        return ("npm", "test", "--")
    if manager == "pnpm":
        return ("pnpm", "test", "--")
    if manager == "yarn":
        return ("yarn", "run", "test")
    raise TestCommandDetectionError("Node package manager is unsupported")


def _node_arguments(framework: str, file_path: str, name: str) -> Tuple[str, ...]:
    exact_name = f"^{re.escape(name)}$"
    if framework == "jest":
        return (
            "--runInBand",
            "--runTestsByPath",
            file_path,
            "--testNamePattern",
            exact_name,
        )
    if framework == "vitest":
        return ("--run", file_path, "--testNamePattern", exact_name)
    if framework == "angular":
        return (
            "--watch=false",
            f"--include={file_path}",
            f"--filter={exact_name}",
        )
    raise TestCommandDetectionError("Node test framework is unsupported")


def _node_plan(
    root: Path,
    case: TestCasePlan,
    name: str,
) -> TestCommandPlan:
    try:
        metadata = load_node_project(root)
    except ValueError as error:
        raise TestCommandDetectionError(str(error)) from error
    command = _script_prefix(metadata.package_manager) + _node_arguments(
        metadata.test_framework,
        case.test_file,
        name,
    )
    return TestCommandPlan(
        "typescript",
        metadata.package_manager,
        metadata.test_framework,
        case.test_file,
        name,
        command,
    )


def detect_test_command(root: Path, case: TestCasePlan) -> TestCommandPlan:
    """Detect a tokenized command for exactly one planned test without running it."""
    if not isinstance(case, TestCasePlan):
        raise TestCommandDetectionError("Current test must be a TestCasePlan")
    path = _test_path(case.test_file)
    suffix = path.suffix.lower()
    is_java = suffix in JAVA_TEST_SUFFIXES
    name = _test_name(case.test_name, java=is_java)
    if is_java:
        return _java_plan(root, case, path, name)
    if suffix in NODE_TEST_SUFFIXES:
        return _node_plan(root, case, name)
    raise TestCommandDetectionError("Test file extension is unsupported")
