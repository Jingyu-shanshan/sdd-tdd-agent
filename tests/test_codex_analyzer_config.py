from pathlib import Path

import pytest

from sdd_tdd_agent.analyze_command import (
    AnalyzerConfigurationError,
    load_analyzer_config,
)


def test_should_load_explicit_codex_exec_protocol(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 300
""",
        encoding="utf-8",
    )

    config = load_analyzer_config(tmp_path)

    assert config.protocol == "codex-exec"
    assert config.command == ("codex",)
    assert config.timeout_seconds == 300


@pytest.mark.parametrize(
    "protocol_lines",
    [
        "requirement_analyzer_protocol: unknown",
        "requirement_analyzer_protocol:",
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_protocol: json-command""",
    ],
)
def test_should_reject_invalid_analyzer_protocol(
    tmp_path: Path,
    protocol_lines: str,
) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        f"""\
{protocol_lines}
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 300
""",
        encoding="utf-8",
    )

    with pytest.raises(
        AnalyzerConfigurationError,
        match="Invalid analyzer protocol config",
    ):
        load_analyzer_config(tmp_path)


def test_should_reject_multi_token_codex_protocol_command(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
  - "extra"
requirement_analyzer_timeout_seconds: 300
""",
        encoding="utf-8",
    )

    with pytest.raises(
        AnalyzerConfigurationError,
        match="Codex analyzer command must contain one executable",
    ):
        load_analyzer_config(tmp_path)
