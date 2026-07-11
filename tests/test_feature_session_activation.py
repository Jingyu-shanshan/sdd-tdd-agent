from pathlib import Path

import pytest

from sdd_tdd_agent.feature_session import create_feature_session


@pytest.mark.parametrize(
    ("initial_metadata", "expected_metadata"),
    [
        (
            "name: example\ncurrent_session: old-session\nbuild_tool: maven\n",
            "name: example\ncurrent_session: new-session\nbuild_tool: maven\n",
        ),
        (
            "name: example\nbuild_tool: gradle\n",
            "name: example\nbuild_tool: gradle\ncurrent_session: new-session\n",
        ),
    ],
)
def test_should_activate_session_without_changing_other_metadata(
    tmp_path: Path,
    initial_metadata: str,
    expected_metadata: str,
) -> None:
    workspace = tmp_path / ".agent"
    (workspace / "sessions").mkdir(parents=True)
    project_metadata = workspace / "project.yml"
    project_metadata.write_text(initial_metadata, encoding="utf-8")

    create_feature_session(
        tmp_path,
        "New feature",
        session_id="new-session",
    )

    assert project_metadata.read_text(encoding="utf-8") == expected_metadata
