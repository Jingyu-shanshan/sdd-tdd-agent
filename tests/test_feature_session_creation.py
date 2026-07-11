import json
from pathlib import Path

from sdd_tdd_agent.feature_session import create_feature_session


def test_should_create_complete_feature_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    (workspace / "sessions").mkdir(parents=True)
    (workspace / "project.yml").write_text("name: example\n", encoding="utf-8")

    session = create_feature_session(
        tmp_path,
        "  Support PDF export  ",
        session_id="20260711-support-pdf-export",
    )

    assert session.session_id == "20260711-support-pdf-export"
    assert session.path == workspace / "sessions" / session.session_id
    assert {path.name for path in session.path.iterdir()} == {
        "requirement.md",
        "design.md",
        "tasks.md",
        "acceptance.md",
        "test-plan.md",
        "implementation.md",
        "review.md",
        "state.json",
    }
    assert "Support PDF export" in (session.path / "requirement.md").read_text(
        encoding="utf-8"
    )
    state = json.loads((session.path / "state.json").read_text(encoding="utf-8"))
    assert state == {
        "session_id": session.session_id,
        "kind": "feature",
        "state": "ANALYSIS",
        "current_task": None,
        "current_cycle": 0,
    }
