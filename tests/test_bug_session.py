import io
import json
import re
from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.analyze_command import analyze_active_requirement
from sdd_tdd_agent.bug_session import create_bug_session
from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult


ARTIFACTS = {
    "requirement.md",
    "design.md",
    "tasks.md",
    "acceptance.md",
    "test-plan.md",
    "implementation.md",
    "review.md",
    "state.json",
}


def _workspace(root: Path, metadata: str = "name: example\n") -> Path:
    workspace = root / ".agent"
    (workspace / "sessions").mkdir(parents=True)
    (workspace / "project.yml").write_text(metadata, encoding="utf-8")
    return workspace


class BugAnalysisRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(
            0,
            json.dumps(
                {
                    "summary": "Fix the export crash.",
                    "user_stories": ["A user exports without a crash."],
                    "functional_requirements": ["Handle empty reports."],
                    "non_functional_requirements": [],
                    "impact_analysis": [],
                    "open_questions": [],
                }
            ),
            "",
        )


def test_should_create_complete_bug_session(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    session = create_bug_session(
        tmp_path,
        "  Fix PDF export crash  ",
        session_id="bug-pdf-export-crash",
    )

    assert session.session_id == "bug-pdf-export-crash"
    assert session.path == workspace / "sessions" / session.session_id
    assert {path.name for path in session.path.iterdir()} == ARTIFACTS
    requirement = (session.path / "requirement.md").read_text(encoding="utf-8")
    assert "Fix PDF export crash" in requirement
    state = json.loads((session.path / "state.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": "bug-pdf-export-crash",
        "kind": "bug",
        "state": "ANALYSIS",
        "current_task": None,
        "current_cycle": 0,
    }


def test_should_create_and_report_bug_session_from_cli(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["bug", "Fix", "empty", "export"],
        out=output,
        root=tmp_path,
    )

    assert exit_code == 0
    match = re.fullmatch(
        r"Created bug session: ([A-Za-z0-9][A-Za-z0-9._-]*)\n",
        output.getvalue(),
    )
    assert match is not None
    session_id = match.group(1)
    assert (workspace / "sessions" / session_id).is_dir()
    metadata = (workspace / "project.yml").read_text(encoding="utf-8")
    assert f"current_session: {session_id}\n" in metadata


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (
            "name: example\ncurrent_session: old\nbuild_tool: maven\n",
            "name: example\ncurrent_session: bug-1\nbuild_tool: maven\n",
        ),
        (
            "name: example\nbuild_tool: gradle\n",
            "name: example\nbuild_tool: gradle\ncurrent_session: bug-1\n",
        ),
    ],
)
def test_should_activate_bug_without_changing_other_metadata(
    tmp_path: Path,
    metadata: str,
    expected: str,
) -> None:
    workspace = _workspace(tmp_path, metadata)

    create_bug_session(tmp_path, "Fix it", session_id="bug-1")

    assert (workspace / "project.yml").read_text(encoding="utf-8") == expected


def test_should_reject_blank_bug_before_mutation(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(ValueError, match="Bug description must not be empty"):
        main(["bug", "   "], root=tmp_path)

    assert list((workspace / "sessions").iterdir()) == []


def test_should_reject_unsafe_bug_session_id(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(ValueError, match="Invalid session identifier"):
        create_bug_session(tmp_path, "Fix it", session_id="../unsafe")

    assert list((workspace / "sessions").iterdir()) == []


def test_should_preserve_existing_session_and_activation_on_collision(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path, "name: example\ncurrent_session: old\n")
    existing = workspace / "sessions" / "bug-1"
    existing.mkdir()
    marker = existing / "marker.txt"
    marker.write_text("owned\n", encoding="utf-8")
    before = (workspace / "project.yml").read_text(encoding="utf-8")

    with pytest.raises(FileExistsError):
        create_bug_session(tmp_path, "Fix it", session_id="bug-1")

    assert marker.read_text(encoding="utf-8") == "owned\n"
    assert (workspace / "project.yml").read_text(encoding="utf-8") == before


def test_should_analyze_bug_through_existing_workflow(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: json-command
requirement_analyzer_command:
  - "bridge"
requirement_analyzer_timeout_seconds: 30
""",
        encoding="utf-8",
    )
    (workspace / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (workspace / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    session = create_bug_session(tmp_path, "Fix export", session_id="bug-1")

    run = analyze_active_requirement(tmp_path, BugAnalysisRunner())

    assert run.next_state == "REQUIREMENT_REVIEW"
    state = json.loads((session.path / "state.json").read_text(encoding="utf-8"))
    assert state["kind"] == "bug"
    assert state["state"] == "REQUIREMENT_REVIEW"
