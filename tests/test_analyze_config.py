from pathlib import Path

from sdd_tdd_agent.analyze_command import load_analyzer_config


def test_should_load_tokenized_command_and_explicit_timeout(tmp_path: Path) -> None:
    workspace = tmp_path / ".agent"
    workspace.mkdir()
    (workspace / "config.yml").write_text(
        """\
max_iterations: 20
requirement_analyzer_command:
  - "model bridge"
  - "analyze"
  - "--format=json"
requirement_analyzer_timeout_seconds: 45
max_test_failures: 5
""",
        encoding="utf-8",
    )

    config = load_analyzer_config(tmp_path)

    assert config.command == ("model bridge", "analyze", "--format=json")
    assert config.timeout_seconds == 45.0
