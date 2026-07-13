import io
import json
from pathlib import Path

from sdd_tdd_agent.cli import main


def _create_review_workspace(root: Path) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\nReady for review.\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "REQUIREMENT_REVIEW",
            }
        ),
        encoding="utf-8",
    )
    return session


def test_should_show_active_requirement_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["requirement", "show"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (session / "requirement.md").read_text(
        encoding="utf-8"
    )


def test_should_approve_active_requirement_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(["requirement", "approve"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == "Requirement approved: feature-1 (DESIGN)\n"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DESIGN"


def test_should_reject_active_requirement_from_cli(tmp_path: Path) -> None:
    session = _create_review_workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["requirement", "reject", "Clarify", "the", "format"],
        out=output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == "Requirement rejected: feature-1 (ANALYSIS)\n"
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["requirement_review"]["reason"] == "Clarify the format"


def test_should_report_requirement_review_error_to_stderr(tmp_path: Path) -> None:
    _create_review_workspace(tmp_path)
    error_output = io.StringIO()

    exit_code = main(
        ["requirement", "reject"],
        root=tmp_path,
        err=error_output,
    )

    assert exit_code == 2
    assert error_output.getvalue() == "Error: Rejection reason must not be empty\n"
