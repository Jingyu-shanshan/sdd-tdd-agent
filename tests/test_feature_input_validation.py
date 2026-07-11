from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.feature_session import create_feature_session


def test_should_reject_missing_feature_request_before_mutation(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    sessions = workspace / "sessions"
    sessions.mkdir(parents=True)
    (workspace / "project.yml").write_text("name: example\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Feature description must not be empty"):
        main(["feature"], root=tmp_path)

    assert list(sessions.iterdir()) == []


def test_should_reject_unsafe_explicit_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    sessions = workspace / "sessions"
    sessions.mkdir(parents=True)
    (workspace / "project.yml").write_text("name: example\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid session identifier"):
        create_feature_session(
            tmp_path,
            "Valid request",
            session_id="../unsafe",
        )

    assert list(sessions.iterdir()) == []
