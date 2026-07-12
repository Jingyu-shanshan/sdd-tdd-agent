from pathlib import Path
from typing import Tuple

import pytest

from sdd_tdd_agent.analyze_command import ActiveSessionError, analyze_active_requirement
from sdd_tdd_agent.model_adapter import ProcessResult


class UnexpectedRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        raise AssertionError("Runner must not be called without an active Session")


def test_should_reject_missing_active_session_before_runner(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")

    with pytest.raises(ActiveSessionError, match="Project has no active Session"):
        analyze_active_requirement(tmp_path, UnexpectedRunner())
