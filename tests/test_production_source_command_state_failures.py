import json
from pathlib import Path

import pytest

from sdd_tdd_agent.production_source_command import _state, _write_state
from sdd_tdd_agent.red_execution import RedExecutionError


@pytest.mark.parametrize("content", ["not-json", "[]"])
def test_should_reject_unreadable_or_nonobject_command_state(
    tmp_path: Path,
    content: str,
) -> None:
    session = tmp_path / ".agent" / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (session / "state.json").write_text(content, encoding="utf-8")

    with pytest.raises(RedExecutionError, match="state"):
        _state(tmp_path, "feature-1")


def test_should_reject_atomic_state_temporary_collision(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state": "RED"}), encoding="utf-8")
    temporary = tmp_path / ".state.json.production-source.tmp"
    temporary.write_text("occupied", encoding="utf-8")

    with pytest.raises(RedExecutionError, match="already in progress"):
        _write_state(state_path, {"state": "IMPLEMENT"})

    assert temporary.read_text(encoding="utf-8") == "occupied"
