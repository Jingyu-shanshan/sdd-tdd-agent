import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from sdd_tdd_agent.test_source_adapter import TestSourceGeneratorError
from sdd_tdd_agent.test_source_command import generate_active_test_source


def _case() -> TestCasePlan:
    return TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export a report",
        "Prove export.",
        "tests/test_export.py",
        "test_should_export_report",
        (),
        "Export it.",
        ("A PDF is returned.",),
        (),
    )


def _response() -> dict[str, str]:
    return {
        "test_id": "TC1",
        "file_path": "tests/test_export.py",
        "content": "def test_should_export_report():\n    assert False\n",
    }


def _workspace(
    root: Path,
    protocol: str = "json-command",
    progress: object = None,
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "export.py").write_text("def export(): ...\n")
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        f"""\
requirement_analyzer_protocol: {protocol}
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 30
""",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\nUse export().\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export\n",
        encoding="utf-8",
    )
    plan_request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan("One case.", (_case(),), (), ())
    (session / "test-plan.md").write_text(
        render_test_plan(plan_request, plan),
        encoding="utf-8",
    )
    state: dict[str, object] = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": None,
        "current_cycle": 0,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
    }
    if progress is not None:
        state["current_task"] = "T1"
        state["current_cycle"] = 1
        state["tdd_cycle"] = progress
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


class JsonRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.command: Optional[Tuple[str, ...]] = None
        self.stdin: Optional[str] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.stdin = stdin
        return ProcessResult(self.returncode, json.dumps(_response()), "SECRET")


class CodexRunner:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.command: Optional[Tuple[str, ...]] = None
        self.isolated_root: Optional[Path] = None
        self.existed_during_run = False

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        self.isolated_root = Path(command[command.index("--cd") + 1])
        self.existed_during_run = self.isolated_root.is_dir()
        assert self.isolated_root != self.project_root
        assert self.project_root not in self.isolated_root.parents
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_response()), encoding="utf-8")
        return ProcessResult(0, "", "")


class FixedResolver:
    def resolve(self, executable: str) -> str:
        return "resolved-codex"


class UnexpectedRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Runner must not be called")


def test_should_generate_and_write_active_test_through_json_provider(
    tmp_path: Path,
) -> None:
    session = _workspace(tmp_path)
    runner = JsonRunner()

    run = generate_active_test_source(tmp_path, runner)

    assert runner.command == ("codex",)
    assert runner.stdin is not None
    payload = json.loads(runner.stdin)
    assert payload["sources"] == [
        {"path": "src/export.py", "content": "def export(): ...\n"}
    ]
    assert run.session_id == "feature-1"
    assert run.test_id == "TC1"
    assert run.file_path == "tests/test_export.py"
    assert run.cycle_number == 1
    assert (tmp_path / "tests" / "test_export.py").read_text() == _response()["content"]
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "WRITE_TEST"


def test_should_resume_existing_write_cycle_without_increment(tmp_path: Path) -> None:
    session = _workspace(
        tmp_path,
        progress={
            "current_test": "TC1",
            "phase": "WRITE_TEST",
            "completed_tests": [],
        },
    )

    run = generate_active_test_source(tmp_path, JsonRunner())

    assert run.cycle_number == 1
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["current_cycle"] == 1


def test_should_run_codex_in_project_external_isolated_directory(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path, protocol="codex-exec")
    runner = CodexRunner(tmp_path)

    generate_active_test_source(
        tmp_path,
        runner,
        command_resolver=FixedResolver(),
    )

    assert runner.command is not None
    assert runner.command[0:2] == ("resolved-codex", "exec")
    assert runner.existed_during_run is True
    assert runner.isolated_root is not None
    assert not runner.isolated_root.exists()


def test_should_validate_config_before_starting_cycle(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    (tmp_path / ".agent" / "config.yml").write_text("max_iterations: 20\n")
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Code provider is not configured"):
        generate_active_test_source(tmp_path, UnexpectedRunner())

    assert (session / "state.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "tests" / "test_export.py").exists()


def test_should_leave_recoverable_cycle_when_provider_fails(tmp_path: Path) -> None:
    session = _workspace(tmp_path)

    with pytest.raises(TestSourceGeneratorError, match="exit code 17"):
        generate_active_test_source(tmp_path, JsonRunner(returncode=17))

    assert not (tmp_path / "tests" / "test_export.py").exists()
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["tdd_cycle"]["phase"] == "WRITE_TEST"
    assert state["current_cycle"] == 1


def test_should_reject_continue_during_red_before_provider_call(
    tmp_path: Path,
) -> None:
    session = _workspace(
        tmp_path,
        progress={"current_test": "TC1", "phase": "RED", "completed_tests": []},
    )
    before = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="already active"):
        generate_active_test_source(tmp_path, UnexpectedRunner())

    assert (session / "state.json").read_text(encoding="utf-8") == before


def test_should_run_continue_from_cli(tmp_path: Path) -> None:
    _workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["continue"],
        out=output,
        root=tmp_path,
        runner=JsonRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Test source ready for RED: feature-1 (TC1 -> tests/test_export.py)\n"
    )


def test_should_report_continue_failure_without_traceback(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        progress={"current_test": "TC1", "phase": "RED", "completed_tests": []},
    )
    errors = io.StringIO()

    exit_code = main(
        ["continue"],
        root=tmp_path,
        runner=UnexpectedRunner(),
        err=errors,
    )

    assert exit_code == 2
    assert errors.getvalue() == "Error: A TDD cycle is already active\n"
