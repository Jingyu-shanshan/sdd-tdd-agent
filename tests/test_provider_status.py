import io
from pathlib import Path

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.provider_registry import (
    load_provider_selection,
    render_provider_status,
)


def _write_config(root: Path) -> None:
    workspace = root / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
max_iterations: 20
requirement_analyzer_protocol: codex-exec
requirement_analyzer_command:
  - "codex"
requirement_analyzer_timeout_seconds: 300
""",
        encoding="utf-8",
    )


def test_should_load_and_render_selected_provider(tmp_path: Path) -> None:
    _write_config(tmp_path)

    selection = load_provider_selection(tmp_path)

    assert selection.provider_key == "codex"
    assert selection.protocol == "codex-exec"
    assert selection.timeout_seconds == 300
    assert render_provider_status(selection) == """\
Selected provider: codex
Adapter status: adapter-ready
Protocol: codex-exec
Timeout seconds: 300
"""


def test_should_list_providers_through_cli(tmp_path: Path) -> None:
    output = io.StringIO()

    exit_code = main(["provider", "list"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("codex: adapter-ready")
    assert "claude-code: planned" in output.getvalue()


def test_should_report_selected_provider_through_cli(tmp_path: Path) -> None:
    _write_config(tmp_path)
    output = io.StringIO()

    exit_code = main(["provider", "status"], out=output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue() == """\
Selected provider: codex
Adapter status: adapter-ready
Protocol: codex-exec
Timeout seconds: 300
"""
