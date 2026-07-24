import io
import json
from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.analyze_command import ActiveSessionError
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.design_command import generate_active_design
from sdd_tdd_agent.model_adapter import ProcessResult


def _proposal_payload() -> dict[str, object]:
    return {
        "overview": "Add an export service.",
        "architecture_decisions": ["Keep export outside CLI dispatch."],
        "components": ["Export service."],
        "data_flow": ["Input to service to output."],
        "interfaces": ["PdfExporter.export"],
        "error_handling": ["Reject invalid input."],
        "security_considerations": ["Redact diagnostics."],
        "testing_strategy": ["Inject the writer."],
        "risks_and_tradeoffs": [],
        "open_questions": [],
    }


def _create_design_workspace(root: Path, protocol: str = "json-command") -> Path:
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
    (session / "design.md").write_text("# Design\n\nPending.\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "DESIGN",
                "current_task": None,
                "current_cycle": 0,
                "requirement_review": {"decision": "approved"},
            }
        ),
        encoding="utf-8",
    )
    return session


class JsonDesignRunner:
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
        return ProcessResult(0, json.dumps(_proposal_payload()), "")


class CodexDesignRunner:
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
        output_path.write_text(json.dumps(_proposal_payload()), encoding="utf-8")
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


def test_should_generate_active_design_through_json_provider(tmp_path: Path) -> None:
    session = _create_design_workspace(tmp_path)
    runner = JsonDesignRunner()

    run = generate_active_design(tmp_path, runner)

    assert runner.command == ("codex",)
    assert runner.stdin is not None
    assert json.loads(runner.stdin)["requirement"].startswith("# Requirement Analysis")
    assert run.session_id == "feature-1"
    assert run.next_state == "DESIGN_REVIEW"
    assert "# Design Proposal" in (session / "design.md").read_text(encoding="utf-8")


def test_should_generate_active_design_through_codex_provider(tmp_path: Path) -> None:
    session = _create_design_workspace(tmp_path, protocol="codex-exec")
    runner = CodexDesignRunner()

    run = generate_active_design(
        tmp_path,
        runner,
        command_resolver=FixedResolver(),
    )

    assert runner.command is not None
    assert runner.command[0:2] == ("resolved-codex", "exec")
    assert run.next_state == "DESIGN_REVIEW"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DESIGN_REVIEW"


def test_should_reject_missing_active_session_before_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ActiveSessionError, match="Project has no active Session"):
        generate_active_design(tmp_path, UnexpectedRunner())


def test_should_run_design_from_cli(tmp_path: Path) -> None:
    _create_design_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["design"],
        out=output,
        root=tmp_path,
        runner=JsonDesignRunner(),
    )

    assert exit_code == 0
    assert output.getvalue() == ("Design ready for review: feature-1 (DESIGN_REVIEW)\n")


def test_should_report_design_config_error_without_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text("max_iterations: 20\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps({"state": "DESIGN"}),
        encoding="utf-8",
    )
    errors = io.StringIO()

    exit_code = main(
        ["design"],
        root=tmp_path,
        runner=UnexpectedRunner(),
        err=errors,
    )

    assert exit_code == 2
    assert errors.getvalue().startswith("Error: Code provider is not configured")
