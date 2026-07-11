import json
from pathlib import Path

from sdd_tdd_agent.project_status import load_project_status


def test_should_load_project_and_active_session_status(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "0005-example"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        """\
name: checkout
target_language: java
build_tool: maven
test_frameworks:
  - junit5
current_session: 0005-example
""",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps({"state": "IMPLEMENT"}),
        encoding="utf-8",
    )

    status = load_project_status(tmp_path)

    assert status.project_name == "checkout"
    assert status.target_language == "java"
    assert status.build_tool == "maven"
    assert status.test_frameworks == ("junit5",)
    assert status.current_session == "0005-example"
    assert status.session_state == "IMPLEMENT"
