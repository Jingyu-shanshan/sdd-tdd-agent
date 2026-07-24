import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.analyze_command import ActiveSessionError
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.task_command import generate_active_tasks


def _breakdown_payload() -> dict[str, object]:
    return {
        "summary": "Implement export in two tasks.",
        "tasks": [
            {
                "task_id": "T1",
                "title": "Add export service",
                "objective": "Create the typed boundary.",
                "affected_areas": ["sdd_tdd_agent/export.py"],
                "dependencies": [],
                "acceptance_criteria": ["The service exports a report."],
                "test_targets": ["tests/test_export.py"],
            },
            {
                "task_id": "T2",
                "title": "Connect the CLI",
                "objective": "Expose the service safely.",
                "affected_areas": ["sdd_tdd_agent/cli.py"],
                "dependencies": ["T1"],
                "acceptance_criteria": ["The CLI invokes the service."],
                "test_targets": ["tests/test_export_cli.py"],
            },
        ],
        "global_risks": [],
        "open_questions": [],
    }


def _create_task_workspace(root: Path, protocol: str = "json-command") -> Path:
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
        "# Requirement Analysis\n\n## Summary\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\n## Overview\n\nAdd an export service.\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text("# Tasks\n\nPending.\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "TASK_BREAKDOWN",
                "current_task": None,
                "current_cycle": 0,
                "requirement_review": {"decision": "approved"},
                "design_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


class JsonTaskRunner:
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
        return ProcessResult(0, json.dumps(_breakdown_payload()), "")


class CodexTaskRunner:
    def __init__(self) -> None:
        self.command: Optional[Tuple[str, ...]] = None

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.command = command
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(json.dumps(_breakdown_payload()), encoding="utf-8")
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


def test_should_generate_active_tasks_through_json_provider(tmp_path: Path) -> None:
    session = _create_task_workspace(tmp_path)
    runner = JsonTaskRunner()

    run = generate_active_tasks(tmp_path, runner)

    assert runner.command == ("codex",)
    assert runner.stdin is not None
    payload = json.loads(runner.stdin)
    assert payload["requirement"].startswith("# Requirement Analysis")
    assert payload["design"].startswith("# Design Proposal")
    assert run.session_id == "feature-1"
    assert run.next_state == "TASK_REVIEW"
    assert "## Task T2: Connect the CLI" in (session / "tasks.md").read_text(
        encoding="utf-8"
    )


def test_should_generate_active_tasks_through_codex_provider(tmp_path: Path) -> None:
    session = _create_task_workspace(tmp_path, protocol="codex-exec")
    runner = CodexTaskRunner()

    run = generate_active_tasks(
        tmp_path,
        runner,
        command_resolver=FixedResolver(),
    )

    assert runner.command is not None
    assert runner.command[0:2] == ("resolved-codex", "exec")
    assert run.next_state == "TASK_REVIEW"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "TASK_REVIEW"


def test_should_reject_missing_active_session_before_task_runner(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ActiveSessionError, match="Project has no active Session"):
        generate_active_tasks(tmp_path, UnexpectedRunner())


def test_should_run_tasks_from_cli(tmp_path: Path) -> None:
    _create_task_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["tasks"],
        out=output,
        root=tmp_path,
        runner=JsonTaskRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == "Tasks ready for review: feature-1 (TASK_REVIEW)\n"


def test_should_report_task_config_error_without_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text("max_iterations: 20\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps({"state": "TASK_BREAKDOWN"}),
        encoding="utf-8",
    )
    errors = io.StringIO()

    exit_code = main(
        ["tasks"],
        root=tmp_path,
        runner=UnexpectedRunner(),
        err=errors,
    )

    assert exit_code == 2
    assert errors.getvalue().startswith("Error: Code provider is not configured")
