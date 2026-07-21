from pathlib import Path

import pytest

from sdd_tdd_agent.project_detection import detect_project
from sdd_tdd_agent.test_execution import (
    detect_full_test_command,
    detect_test_command,
)
from sdd_tdd_agent.test_generation import TestCasePlan


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "toolchains"


def _case(test_file: str, test_name: str) -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Calculate",
        "Prove deterministic addition.",
        test_file,
        test_name,
        (),
        "Two numbers are added.",
        ("The expected sum is returned.",),
        (),
    )


@pytest.mark.parametrize(
    ("tool", "single_command", "full_command"),
    [
        (
            "maven",
            ("mvn", "-Dtest=example.CalculatorTest#addsTwoNumbers", "test"),
            ("mvn", "test"),
        ),
        (
            "gradle",
            (
                "gradle",
                "test",
                "--tests",
                "example.CalculatorTest.addsTwoNumbers",
            ),
            ("gradle", "test"),
        ),
    ],
)
def test_should_plan_real_java_fixture_commands(
    tool: str,
    single_command: tuple[str, ...],
    full_command: tuple[str, ...],
) -> None:
    root = FIXTURE_ROOT / tool
    case = _case(
        "src/test/java/example/CalculatorTest.java",
        "addsTwoNumbers",
    )

    profile = detect_project(root)
    single = detect_test_command(root, case)
    full = detect_full_test_command(root, case)

    assert profile is not None
    assert profile.build_tool == tool
    assert profile.test_frameworks == ("junit5",)
    assert single.command == single_command
    assert full.command == full_command


@pytest.mark.parametrize(
    ("manager", "single_prefix", "full_command"),
    [
        ("npm", ("npm", "test", "--"), ("npm", "test", "--", "--run")),
        ("pnpm", ("pnpm", "test", "--"), ("pnpm", "test", "--", "--run")),
        ("yarn", ("yarn", "run", "test"), ("yarn", "run", "test", "--run")),
    ],
)
def test_should_plan_real_node_fixture_commands(
    manager: str,
    single_prefix: tuple[str, ...],
    full_command: tuple[str, ...],
) -> None:
    root = FIXTURE_ROOT / manager
    case = _case("src/calculator.test.ts", "adds two numbers")

    profile = detect_project(root)
    single = detect_test_command(root, case)
    full = detect_full_test_command(root, case)

    assert profile is not None
    assert profile.build_tool == manager
    assert profile.test_frameworks == ("vitest",)
    assert single.command == single_prefix + (
        "--run",
        "src/calculator.test.ts",
        "--testNamePattern",
        r"^adds\ two\ numbers$",
    )
    assert full.command == full_command
