import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.analyze_command import ActiveSessionError
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.test_command import generate_active_test_plan


def _plan_payload() -> dict[str, object]:
    return {
        "summary": "Verify export incrementally.",
        "cases": [
            {
                "test_id": "TC1",
                "task_id": "T1",
                "phase": "happy_path",
                "title": "Verify export",
                "objective": "Prove export succeeds.",
                "test_file": "tests/test_export.py",
                "test_name": "test_should_export",
                "preconditions": [],
                "action": "Invoke export.",
                "expected_outcomes": ["A report is exported."],
                "dependencies": [],
            }
        ],
        "risks": [],
        "open_questions": [],
    }


def _create_workspace(root: Path, protocol: str = "json-command") -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
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
    (workspace / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (workspace / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\nUse an export service.\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export service\n",
        encoding="utf-8",
    )
    (session / "test-plan.md").write_text("# Test Plan\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "state": "TEST_GENERATION",
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
                "task_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


class JsonRunner:
    def __init__(self) -> None:
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
        return ProcessResult(0, json.dumps(_plan_payload()), "")


class CodexRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_plan_payload()), encoding="utf-8")
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


def test_should_generate_active_test_plan_through_json_provider(
    tmp_path: Path,
) -> None:
    session = _create_workspace(tmp_path)
    runner = JsonRunner()

    run = generate_active_test_plan(tmp_path, runner)

    assert runner.command == ("codex",)
    assert runner.stdin is not None
    assert "Task T1" in json.loads(runner.stdin)["tasks"]
    assert run.next_state == "IMPLEMENTATION"
    assert "# Test Generation Plan" in (session / "test-plan.md").read_text()


def test_should_generate_active_test_plan_through_codex_provider(
    tmp_path: Path,
) -> None:
    _create_workspace(tmp_path, protocol="codex-exec")
    runner = CodexRunner()

    run = generate_active_test_plan(
        tmp_path,
        runner,
        command_resolver=FixedResolver(),
    )

    assert runner.command is not None
    assert runner.command[0:2] == ("resolved-codex", "exec")
    assert run.next_state == "IMPLEMENTATION"


def test_should_reject_missing_session_before_test_plan_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ActiveSessionError, match="Project has no active Session"):
        generate_active_test_plan(tmp_path, UnexpectedRunner())


def test_should_run_test_plan_generation_from_cli(tmp_path: Path) -> None:
    _create_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["tests"],
        out=output,
        root=tmp_path,
        runner=JsonRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == (
        "Test plan ready for implementation: feature-1 (IMPLEMENTATION)\n"
    )


def test_should_report_test_plan_config_error_without_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text("max_iterations: 20\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps({"session_id": "feature-1", "state": "TEST_GENERATION"}),
        encoding="utf-8",
    )
    errors = io.StringIO()

    exit_code = main(
        ["tests"],
        root=tmp_path,
        runner=UnexpectedRunner(),
        err=errors,
    )

    assert exit_code == 2
    assert errors.getvalue().startswith("Error: Code provider is not configured")
