from pathlib import Path
from typing import Tuple

from sdd_tdd_agent.green_verification import verify_active_implementation
from sdd_tdd_agent.red_execution import TestCommandProcessResult
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from tests.green_verification_support import create_implement_workspace
from tests.production_source_support import test_case


class PassingGreenRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        return TestCommandProcessResult(0, "passed\n", "")


def _next_case() -> TestCasePlan:
    return TestCasePlan(
        "TC2",
        "T2",
        "boundary",
        "Export an empty report",
        "Return an empty report safely.",
        "src/export.boundary.test.ts",
        "exports empty report",
        (),
        "Call exportReport with empty input.",
        ("An empty report is returned.",),
        ("TC1",),
    )


def create_green_workspace(root: Path, include_next: bool = False) -> Path:
    session = create_implement_workspace(root)
    if include_next:
        (session / "tasks.md").write_text(
            "# Task Breakdown\n\n## Task T1: Export\n\n## Task T2: Empty export\n",
            encoding="utf-8",
        )
        request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
        plan = GeneratedTestPlan(
            "Two ordered cases.",
            (test_case(), _next_case()),
            (),
            (),
        )
        (session / "test-plan.md").write_text(
            render_test_plan(request, plan),
            encoding="utf-8",
        )
    verify_active_implementation(root, PassingGreenRunner())
    return session
