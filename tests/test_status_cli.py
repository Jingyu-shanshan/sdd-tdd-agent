import io
import json
from pathlib import Path

from sdd_tdd_agent.cli import main


def test_should_print_project_status(tmp_path: Path) -> None:
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
    output = io.StringIO()

    exit_code = main(["status"], output, tmp_path)

    assert exit_code == 0
    assert output.getvalue() == (
        "Project: checkout\n"
        "Language: java\n"
        "Build tool: maven\n"
        "Test frameworks: junit5\n"
        "Session: 0005-example\n"
        "State: IMPLEMENT\n"
    )
