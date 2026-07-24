import io
import json
from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.provider_registry import (
    ProviderSelectionError,
    select_provider,
)


ORIGINAL_CONFIG = """\
max_iterations: 20
# Preserve this project setting.
requirement_analyzer_protocol: json-command
requirement_analyzer_command:
  - "custom bridge"
  - "analyze"
requirement_analyzer_timeout_seconds: 45
"""


def _write_workspace(root: Path) -> tuple[Path, Path]:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    config_path = workspace / "config.yml"
    config_path.write_text(ORIGINAL_CONFIG, encoding="utf-8")
    state_path = session / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "session_id": "feature-1",
                "kind": "feature",
                "state": "ANALYSIS",
                "current_task": None,
                "current_cycle": 0,
            }
        ),
        encoding="utf-8",
    )
    return config_path, state_path


def test_should_atomically_select_codex_and_preserve_other_config(
    tmp_path: Path,
) -> None:
    config_path, _ = _write_workspace(tmp_path)

    selection = select_provider(tmp_path, "codex")

    assert selection.provider_key == "codex"
    assert selection.timeout_seconds == 45
    assert (
        config_path.read_text(encoding="utf-8")
        == """\
max_iterations: 20
# Preserve this project setting.
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 45
"""
    )
    assert not (config_path.parent / ".config.yml.provider.tmp").exists()


@pytest.mark.parametrize(
    ("provider_key", "message"),
    [
        ("unknown", "Unknown provider: unknown"),
        ("copilot", r"Provider is not selectable: copilot \(planned\)"),
        (
            "custom-json",
            "Provider requires explicit command configuration: custom-json",
        ),
    ],
)
def test_should_preserve_config_and_session_for_invalid_selection(
    tmp_path: Path,
    provider_key: str,
    message: str,
) -> None:
    config_path, state_path = _write_workspace(tmp_path)
    original_state = state_path.read_text(encoding="utf-8")

    with pytest.raises(ProviderSelectionError, match=message):
        select_provider(tmp_path, provider_key)

    assert config_path.read_text(encoding="utf-8") == ORIGINAL_CONFIG
    assert state_path.read_text(encoding="utf-8") == original_state


def test_should_select_provider_through_cli(tmp_path: Path) -> None:
    config_path, _ = _write_workspace(tmp_path)
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["provider", "use", "codex"],
        out=output,
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == "Selected provider for code: codex\n"
    assert error_output.getvalue() == ""
    assert "requirement_analyzer_protocol: codex-exec" in config_path.read_text(
        encoding="utf-8"
    )


def test_should_select_cursor_through_cli(tmp_path: Path) -> None:
    config_path, _ = _write_workspace(tmp_path)
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["provider", "use", "cursor"],
        out=output,
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == "Selected provider for code: cursor\n"
    assert error_output.getvalue() == ""
    assert "requirement_analyzer_protocol: cursor-exec" in config_path.read_text(
        encoding="utf-8"
    )
    assert '  - "cursor-agent"' in config_path.read_text(encoding="utf-8")
