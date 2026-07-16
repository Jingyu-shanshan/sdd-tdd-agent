import io
import json
from pathlib import Path
from typing import Sequence, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.red_execution import (
    TestCommandProcessResult,
)


REQUIREMENT_SENTINEL = "REQUIREMENT-E2E-SENTINEL"
TEST_CONTENT = """\
import { expect, test } from 'vitest'
import { exportReport } from './export'

test('exports report', () => {
  expect(exportReport()).toBe('report')
})
"""
INITIAL_SOURCE = """\
export function exportReport(): string {
  throw new Error('TODO')
}
"""
FINAL_SOURCE = """\
export function exportReport(): string {
  return 'report'
}
"""


MODEL_RESPONSES: Tuple[dict[str, object], ...] = (
    {
        "summary": f"{REQUIREMENT_SENTINEL}: export reports.",
        "user_stories": ["A user can export a report."],
        "functional_requirements": ["Return an exported report."],
        "non_functional_requirements": [],
        "impact_analysis": ["Add one typed export function."],
        "open_questions": [],
    },
    {
        "overview": "Add one export function.",
        "architecture_decisions": ["Keep the function pure."],
        "components": ["Export module."],
        "data_flow": ["Call to report string."],
        "interfaces": ["exportReport(): string"],
        "error_handling": ["Use typed failures."],
        "security_considerations": ["Do not expose secrets."],
        "testing_strategy": ["Verify through Vitest."],
        "risks_and_tradeoffs": [],
        "open_questions": [],
    },
    {
        "summary": "Implement export in one task.",
        "tasks": [
            {
                "task_id": "T1",
                "title": "Add export function",
                "objective": "Return the report string.",
                "affected_areas": ["src/export.ts"],
                "dependencies": [],
                "acceptance_criteria": ["The report is returned."],
                "test_targets": ["src/export.test.ts"],
            }
        ],
        "global_risks": [],
        "open_questions": [],
    },
    {
        "summary": "Verify export incrementally.",
        "cases": [
            {
                "test_id": "TC1",
                "task_id": "T1",
                "phase": "happy_path",
                "title": "Export a report",
                "objective": "Prove export succeeds.",
                "test_file": "src/export.test.ts",
                "test_name": "exports report",
                "preconditions": [],
                "action": "Call exportReport.",
                "expected_outcomes": ["The report is returned."],
                "dependencies": [],
            }
        ],
        "risks": [],
        "open_questions": [],
    },
    {
        "test_id": "TC1",
        "file_path": "src/export.test.ts",
        "content": TEST_CONTENT,
    },
    {
        "test_id": "TC1",
        "file_path": "src/export.ts",
        "content": FINAL_SOURCE,
    },
)


class WorkflowModelRunner:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        self.commands: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        request = json.loads(stdin)
        assert isinstance(request, dict)
        response = MODEL_RESPONSES[len(self.requests)]
        self.requests.append(request)
        self.commands.append(command)
        return ProcessResult(0, json.dumps(response), "")


class WorkflowTestRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[Tuple[str, ...], Path, float]] = []

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        self.calls.append((command, cwd, timeout_seconds))
        if len(self.calls) == 1:
            return TestCommandProcessResult(
                1,
                "src/export.test.ts: exports report failed\n",
                "",
            )
        return TestCommandProcessResult(0, "passed\n", "")


def _run_cli(
    root: Path,
    arguments: Sequence[str],
    model_runner: WorkflowModelRunner,
    test_runner: WorkflowTestRunner,
) -> str:
    output = io.StringIO()
    errors = io.StringIO()
    exit_code = main(
        arguments,
        out=output,
        err=errors,
        root=root,
        runner=model_runner,
        test_runner=test_runner,
    )
    assert exit_code == 0, errors.getvalue()
    assert errors.getvalue() == ""
    return output.getvalue()


def _state(session: Path) -> dict[str, object]:
    value = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _create_project(root: Path) -> None:
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
    (source / "export.ts").write_text(INITIAL_SOURCE, encoding="utf-8")


def _initialize_session(
    root: Path,
    model_runner: WorkflowModelRunner,
    test_runner: WorkflowTestRunner,
) -> tuple[Path, str]:
    assert _run_cli(root, ["init"], model_runner, test_runner) == (
        "Initialized .agent workspace.\n"
    )
    config_path = root / ".agent" / "config.yml"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace(
        "test_command_timeout_seconds: 300",
        "test_command_timeout_seconds: 15",
    ).replace(
        "full_test_suite_timeout_seconds: 900",
        "full_test_suite_timeout_seconds: 60",
    )
    config_path.write_text(
        config
        + "requirement_analyzer_protocol: json-command\n"
        + "requirement_analyzer_command:\n"
        + '  - "model-bridge"\n'
        + "requirement_analyzer_timeout_seconds: 30\n",
        encoding="utf-8",
    )
    _run_cli(
        root,
        ["feature", f"{REQUIREMENT_SENTINEL} export reports"],
        model_runner,
        test_runner,
    )
    session_id = load_project_status(root).current_session
    assert session_id is not None
    session = root / ".agent" / "sessions" / session_id
    assert _state(session)["state"] == "ANALYSIS"
    return session, session_id


def _run_sdd_workflow(
    root: Path,
    session: Path,
    model_runner: WorkflowModelRunner,
    test_runner: WorkflowTestRunner,
) -> None:
    commands = (
        (["analyze"], "REQUIREMENT_REVIEW"),
        (["requirement", "approve"], "DESIGN"),
        (["design"], "DESIGN_REVIEW"),
        (["design", "approve"], "TASK_BREAKDOWN"),
        (["tasks"], "TASK_REVIEW"),
        (["tasks", "approve"], "TEST_GENERATION"),
        (["tests"], "IMPLEMENTATION"),
    )
    for arguments, expected_state in commands:
        _run_cli(root, arguments, model_runner, test_runner)
        assert _state(session)["state"] == expected_state


def _run_implementation_workflow(
    root: Path,
    session: Path,
    session_id: str,
    model_runner: WorkflowModelRunner,
    test_runner: WorkflowTestRunner,
) -> None:
    outputs = [
        _run_cli(root, ["continue"], model_runner, test_runner) for _ in range(5)
    ]
    assert outputs == [
        f"Test source ready for RED: {session_id} (TC1 -> src/export.test.ts)\n",
        f"RED confirmed: {session_id} (TC1, exit 1)\n",
        f"Production source ready for GREEN: {session_id} (TC1 -> src/export.ts)\n",
        f"GREEN confirmed: {session_id} (TC1; current test and full suite passed)\n",
        f"Implementation ready for review: {session_id} (1 tests GREEN)\n",
    ]
    assert _state(session)["state"] == "REVIEW"
    _run_cli(root, ["review"], model_runner, test_runner)
    assert _state(session)["state"] == "REFACTOR"
    _run_cli(root, ["refactor"], model_runner, test_runner)


def _assert_done(root: Path, session: Path) -> None:
    final_state = _state(session)
    assert final_state["state"] == "DONE"
    assert final_state["refactor"] == {
        "mode": "no_source_change",
        "decision": "verified",
    }
    assert "implementation_completion" in final_state
    assert "implementation_review" in final_state
    assert "final_verification" in final_state
    assert (root / "src" / "export.ts").read_text(encoding="utf-8") == FINAL_SOURCE


def _assert_runner_contracts(
    root: Path,
    model_runner: WorkflowModelRunner,
    test_runner: WorkflowTestRunner,
) -> None:
    current = (
        "npm",
        "test",
        "--",
        "--run",
        "src/export.test.ts",
        "--testNamePattern",
        r"^exports\ report$",
    )
    suite = ("npm", "test", "--", "--run")
    assert [call[0] for call in test_runner.calls] == [
        current,
        current,
        suite,
        current,
        suite,
    ]
    assert [call[1] for call in test_runner.calls] == [root.resolve()] * 5
    assert [call[2] for call in test_runner.calls] == [15.0, 15.0, 60.0, 15.0, 60.0]
    assert model_runner.commands == [("model-bridge",)] * 6
    assert REQUIREMENT_SENTINEL in json.dumps(model_runner.requests[4])
    assert REQUIREMENT_SENTINEL not in json.dumps(model_runner.requests[5])


def test_should_complete_full_sdd_tdd_workflow_through_public_cli(
    tmp_path: Path,
) -> None:
    _create_project(tmp_path)
    model_runner = WorkflowModelRunner()
    test_runner = WorkflowTestRunner()
    session, session_id = _initialize_session(tmp_path, model_runner, test_runner)
    _run_sdd_workflow(tmp_path, session, model_runner, test_runner)
    _run_implementation_workflow(
        tmp_path,
        session,
        session_id,
        model_runner,
        test_runner,
    )
    _assert_done(tmp_path, session)
    _assert_runner_contracts(tmp_path, model_runner, test_runner)
