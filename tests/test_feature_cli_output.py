import io
import re
from pathlib import Path

from sdd_tdd_agent.cli import main


def test_should_report_created_feature_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    (workspace / "sessions").mkdir(parents=True)
    (workspace / "project.yml").write_text("name: example\n", encoding="utf-8")
    output = io.StringIO()

    exit_code = main(["feature", "Add search"], out=output, root=tmp_path)

    assert exit_code == 0
    match = re.fullmatch(
        r"Created feature session: ([A-Za-z0-9][A-Za-z0-9._-]*)\n",
        output.getvalue(),
    )
    assert match is not None
    assert (workspace / "sessions" / match.group(1)).is_dir()
