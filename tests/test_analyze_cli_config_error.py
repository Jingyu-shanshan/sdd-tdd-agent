import io
import json
from pathlib import Path
from typing import Tuple

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.model_adapter import ProcessResult


class UnexpectedConfigErrorRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Runner must not run with incomplete configuration")


def test_should_report_incomplete_analyzer_config_without_traceback(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text(
        "name: reports\ncurrent_session: feature-1\n",
        encoding="utf-8",
    )
    (workspace / "config.yml").write_text(
        "max_iterations: 20\n",
        encoding="utf-8",
    )
    (session / "state.json").write_text(
        json.dumps({"state": "ANALYSIS"}),
        encoding="utf-8",
    )
    output = io.StringIO()
    errors = io.StringIO()

    exit_code = main(
        ["analyze"],
        out=output,
        root=tmp_path,
        runner=UnexpectedConfigErrorRunner(),
        err=errors,
    )

    assert exit_code == 2
    assert output.getvalue() == ""
    assert errors.getvalue() == (
        "Error: Analyzer configuration is incomplete; add "
        "requirement_analyzer_command and requirement_analyzer_timeout_seconds "
        "to .agent/config.yml\n"
    )
    assert json.loads((session / "state.json").read_text(encoding="utf-8")) == {
        "state": "ANALYSIS"
    }
