from pathlib import Path

import pytest

from sdd_tdd_agent.analyze_command import (
    AnalyzerConfigurationError,
    load_analyzer_config,
)
from sdd_tdd_agent.model_adapter import CommandAnalyzerConfig


def test_should_reject_whitespace_only_direct_command_argument() -> None:
    with pytest.raises(ValueError, match="non-empty arguments"):
        CommandAnalyzerConfig(command=("   ",), timeout_seconds=10.0)


def test_should_reject_whitespace_only_config_command_argument(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_command:
  - "   "
requirement_analyzer_timeout_seconds: 10
""",
        encoding="utf-8",
    )

    with pytest.raises(AnalyzerConfigurationError, match="configuration is invalid"):
        load_analyzer_config(tmp_path)
