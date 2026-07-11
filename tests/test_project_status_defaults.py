from pathlib import Path

from sdd_tdd_agent.project_status import load_project_status, render_project_status


def test_should_use_defaults_without_classification_or_session(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text(
        "name: empty-project\n",
        encoding="utf-8",
    )

    status = load_project_status(tmp_path)

    assert status.target_language == "unknown"
    assert status.build_tool == "unknown"
    assert status.test_frameworks == ()
    assert status.current_session is None
    assert status.session_state is None
    assert render_project_status(status) == (
        "Project: empty-project\n"
        "Language: unknown\n"
        "Build tool: unknown\n"
        "Test frameworks: none\n"
        "Session: none\n"
        "State: none\n"
    )
