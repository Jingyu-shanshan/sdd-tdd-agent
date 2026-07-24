import io
from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.provider_registry import (
    ProviderSelectionError,
    load_provider_config,
    select_provider,
)


CONFIG = """\
max_iterations: 20
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 45
"""


def _write_config(root: Path) -> Path:
    workspace = root / ".agent"
    workspace.mkdir()
    path = workspace / "config.yml"
    path.write_text(CONFIG, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("role", "provider_key", "expected_protocol", "expected_command"),
    [
        ("test-source", "claude-code", "claude-exec", ("claude",)),
        ("production-source", "cursor", "cursor-exec", ("cursor-agent",)),
    ],
)
def test_should_select_provider_for_source_role(
    tmp_path: Path,
    role: str,
    provider_key: str,
    expected_protocol: str,
    expected_command: tuple[str, ...],
) -> None:
    config_path = _write_config(tmp_path)

    selection = select_provider(tmp_path, provider_key, role)
    config = load_provider_config(tmp_path, role)

    assert selection.provider_key == provider_key
    assert selection.role == role
    assert config.protocol == expected_protocol
    assert config.command == expected_command
    assert config.timeout_seconds == 45
    assert "requirement_analyzer_protocol: codex-exec" in config_path.read_text(
        encoding="utf-8"
    )


def test_should_fall_back_to_default_provider_for_unconfigured_role(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path)

    config = load_provider_config(tmp_path, "test-source")

    assert config.protocol == "codex-exec"
    assert config.command == ("codex",)


@pytest.mark.parametrize(
    ("role", "provider_key", "config_line"),
    [
        ("test", "claude-code", "test_source_provider: claude-code"),
        ("code", "cursor", "production_source_provider: cursor"),
    ],
)
def test_should_select_role_provider_through_cli(
    tmp_path: Path,
    role: str,
    provider_key: str,
    config_line: str,
) -> None:
    config_path = _write_config(tmp_path)
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["provider", "use", provider_key, "--for", role],
        out=output,
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == f"Selected provider for {role}: {provider_key}\n"
    assert error_output.getvalue() == ""
    assert config_line in config_path.read_text(encoding="utf-8")


def test_should_report_role_provider_through_cli(tmp_path: Path) -> None:
    _write_config(tmp_path)
    select_provider(tmp_path, "claude-code", "test-source")
    output = io.StringIO()

    exit_code = main(
        ["provider", "status", "--for", "test"],
        out=output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue().startswith("Selected provider: claude-code\n")


def test_should_reject_unknown_provider_role_without_modifying_config(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path)

    with pytest.raises(ProviderSelectionError, match="Unknown provider role: review"):
        select_provider(tmp_path, "codex", "review")

    assert config_path.read_text(encoding="utf-8") == CONFIG
