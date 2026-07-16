import io
import json
from pathlib import Path
from typing import Optional, Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.implementation_command import continue_active_implementation
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.red_execution import (
    TestCommandProcessResult,
    record_test_source_artifact,
)
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from sdd_tdd_agent.test_source_command import TestSourceCommandRun
from sdd_tdd_agent.test_source_generation import GeneratedTestSource


TEST_CONTENT = "test('exports report', () => { expect(false).toBe(true) })\n"


def _case() -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export",
        "Prove export.",
        "src/export.test.ts",
        "exports report",
        (),
        "Export.",
        ("It works.",),
        (),
    )


def _workspace(root: Path) -> Path:
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
    (root / "src").mkdir()
    (root / "src" / "export.ts").write_text("export function exportReport() {}\n")
    for name, content in (
        ("requirement.md", "# Requirement Analysis\n\nExport.\n"),
        ("design.md", "# Design Proposal\n\nUse exportReport.\n"),
        ("tasks.md", "# Task Breakdown\n\n## Task T1: Export\n"),
    ):
        (session / name).write_text(content, encoding="utf-8")
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    (session / "test-plan.md").write_text(
        render_test_plan(
            request,
            GeneratedTestPlan("One case.", (_case(),), (), ()),
        ),
        encoding="utf-8",
    )
    state = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


class SourceRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls += 1
        response = {
            "test_id": "TC1",
            "file_path": "src/export.test.ts",
            "content": TEST_CONTENT,
        }
        return ProcessResult(0, json.dumps(response), "")


class UnexpectedModelRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Model runner must not be called")


class RedRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> TestCommandProcessResult:
        self.command = command
        return TestCommandProcessResult(1, "src/export.test.ts failed", "")


def test_should_generate_test_then_record_source_marker(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    model_runner = SourceRunner()
    test_runner = RedRunner()

    run = continue_active_implementation(tmp_path, model_runner, test_runner)

    assert isinstance(run, TestSourceCommandRun)
    assert model_runner.calls == 1
    assert test_runner.command is None
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "WRITE_TEST"
    assert state["test_source"]["test_id"] == "TC1"
    assert len(state["test_source"]["sha256"]) == 64


def test_should_execute_red_without_calling_model_runner(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["current_task"] = "T1"
    state["current_cycle"] = 1
    state["tdd_cycle"] = {
        "current_test": "TC1",
        "phase": "WRITE_TEST",
        "completed_tests": [],
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    test_file = tmp_path / "src" / "export.test.ts"
    test_file.write_text(TEST_CONTENT, encoding="utf-8")
    record_test_source_artifact(
        tmp_path,
        "feature-1",
        GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
    )
    test_runner = RedRunner()

    run = continue_active_implementation(
        tmp_path,
        UnexpectedModelRunner(),
        test_runner,
    )

    assert run.test_id == "TC1"
    assert test_runner.command is not None
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "RED"


def test_should_render_deterministic_red_cli_output(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["current_task"] = "T1"
    state["current_cycle"] = 1
    state["tdd_cycle"] = {
        "current_test": "TC1",
        "phase": "WRITE_TEST",
        "completed_tests": [],
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (tmp_path / "src" / "export.test.ts").write_text(
        TEST_CONTENT,
        encoding="utf-8",
    )
    record_test_source_artifact(
        tmp_path,
        "feature-1",
        GeneratedTestSource("TC1", "src/export.test.ts", TEST_CONTENT),
    )
    output = io.StringIO()

    exit_code = main(
        ["continue"],
        out=output,
        root=tmp_path,
        runner=UnexpectedModelRunner(),
        test_runner=RedRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == "RED confirmed: feature-1 (TC1, exit 1)\n"
