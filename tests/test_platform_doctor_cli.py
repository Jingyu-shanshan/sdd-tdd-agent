import io
from pathlib import Path

from sdd_tdd_agent.cli import main


def test_should_diagnose_host_without_mutating_project_state(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    project_path = workspace / "project.yml"
    state_path = workspace / "state.json"
    project_content = "name: example\ncurrent_session: feature-1\n"
    state_content = '{"state": "REQUIREMENT_REVIEW"}\n'
    project_path.write_text(project_content, encoding="utf-8")
    state_path.write_text(state_content, encoding="utf-8")
    output = io.StringIO()

    exit_code = main(["platform", "doctor"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Operating system: ")
    assert "\nDistribution: " in output.getvalue()
    assert "\nPlatform support: " in output.getvalue()
    assert "\nPython: " in output.getvalue()
    assert "\nTemporary directory: " in output.getvalue()
    assert output.getvalue().endswith("\n")
    assert project_path.read_text(encoding="utf-8") == project_content
    assert state_path.read_text(encoding="utf-8") == state_content
