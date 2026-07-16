from pathlib import Path

from sdd_tdd_agent.project_init import initialize_project


def test_should_bootstrap_explicit_test_command_timeout(tmp_path: Path) -> None:
    initialize_project(tmp_path)

    config = (tmp_path / ".agent" / "config.yml").read_text(encoding="utf-8")
    assert "test_command_timeout_seconds: 300\n" in config
