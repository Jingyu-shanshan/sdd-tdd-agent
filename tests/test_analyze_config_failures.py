from pathlib import Path

import pytest

from sdd_tdd_agent.analyze_command import (
    AnalyzerConfigurationError,
    load_analyzer_config,
)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("max_iterations: 20\n", "Analyzer configuration is incomplete"),
        (
            """\
requirement_analyzer_command: "bridge"
requirement_analyzer_timeout_seconds: 10
""",
            "Invalid analyzer command config",
        ),
        (
            """\
requirement_analyzer_command:
  - bridge
requirement_analyzer_timeout_seconds: 10
""",
            "Analyzer command items must be JSON strings",
        ),
        (
            """\
requirement_analyzer_command:
  - 42
requirement_analyzer_timeout_seconds: 10
""",
            "Analyzer command items must be non-empty JSON strings",
        ),
        (
            """\
requirement_analyzer_command:
  - "bridge"
""",
            "Analyzer configuration is incomplete",
        ),
        (
            """\
requirement_analyzer_command:
  - "bridge"
requirement_analyzer_timeout_seconds: invalid
""",
            "Invalid analyzer timeout config",
        ),
        (
            """\
requirement_analyzer_command:
  - "bridge"
requirement_analyzer_timeout_seconds: 10
requirement_analyzer_timeout_seconds: 20
""",
            "Invalid analyzer timeout config",
        ),
        (
            """\
requirement_analyzer_command:
  - "bridge"
requirement_analyzer_command:
  - "other"
requirement_analyzer_timeout_seconds: 10
""",
            "Invalid analyzer command config",
        ),
        (
            """\
requirement_analyzer_command:
requirement_analyzer_timeout_seconds: 0
""",
            "Analyzer configuration is invalid",
        ),
    ],
)
def test_should_reject_invalid_analyzer_config(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(content, encoding="utf-8")

    with pytest.raises(AnalyzerConfigurationError, match=message) as captured:
        load_analyzer_config(tmp_path)

    assert "bridge" not in str(captured.value)
    assert "other" not in str(captured.value)
