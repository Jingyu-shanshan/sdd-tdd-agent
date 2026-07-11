import re
from pathlib import Path

from sdd_tdd_agent.cli import main


def test_should_create_feature_session_from_cli(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    (workspace / "sessions").mkdir(parents=True)
    (workspace / "project.yml").write_text("name: example\n", encoding="utf-8")

    exit_code = main(["feature", "Add", "PDF export"], root=tmp_path)

    assert exit_code == 0
    active_line = (workspace / "project.yml").read_text(encoding="utf-8").splitlines()
    session_id = next(
        line.removeprefix("current_session: ")
        for line in active_line
        if line.startswith("current_session: ")
    )
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id)
    requirement = (workspace / "sessions" / session_id / "requirement.md").read_text(
        encoding="utf-8"
    )
    assert "Add PDF export" in requirement
