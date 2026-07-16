import json
from pathlib import Path
from typing import Tuple

from sdd_tdd_agent.red_execution import (
    TestCommandProcessResult,
    execute_current_test_for_red,
    record_test_source_artifact,
)
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from sdd_tdd_agent.test_source_generation import GeneratedTestSource


TEST_CONTENT = """\
import { expect, test } from 'vitest'
import { exportReport } from './export'

test('exports report', () => {
  expect(exportReport()).toBe('report')
})
"""
PRODUCTION_CONTENT = """\
export function exportReport(): string {
  throw new Error('TODO')
}
"""
GENERATED_CONTENT = """\
export function exportReport(): string {
  return 'report'
}
"""


def test_case() -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export a report",
        "Return the report.",
        "src/export.test.ts",
        "exports report",
        (),
        "Call exportReport.",
        ("The report is returned.",),
        (),
    )


class AttributableRedRunner:
    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        return TestCommandProcessResult(
            1,
            "src/export.test.ts: exports report failed\n",
            "",
        )


def create_red_workspace(root: Path) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: json-command
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 30
test_command_timeout_seconds: 15
""",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "reports",
                "packageManager": "npm@11.0.0",
                "scripts": {"test": "vitest"},
                "devDependencies": {"vitest": "4.0.0"},
            }
        ),
        encoding="utf-8",
    )
    source = root / "src"
    source.mkdir()
    (source / "export.ts").write_text(PRODUCTION_CONTENT, encoding="utf-8")
    (source / "export.test.ts").write_text(TEST_CONTENT, encoding="utf-8")
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\nREQUIREMENT-SENTINEL\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\nDESIGN-SENTINEL\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export\n\nTASK-SENTINEL\n",
        encoding="utf-8",
    )
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan("One case.", (test_case(),), (), ())
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    state = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": "T1",
        "current_cycle": 1,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
        "tdd_cycle": {
            "current_test": "TC1",
            "phase": "WRITE_TEST",
            "completed_tests": [],
        },
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    record_test_source_artifact(
        root,
        "feature-1",
        GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
    )
    execute_current_test_for_red(
        root,
        "feature-1",
        AttributableRedRunner(),
        15.0,
    )
    return session
