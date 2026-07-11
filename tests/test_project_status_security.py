from pathlib import Path

import pytest

from sdd_tdd_agent.project_status import load_project_status


def test_should_reject_session_path_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text(
        "name: unsafe-project\ncurrent_session: ../../outside\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid session identifier"):
        load_project_status(tmp_path)
