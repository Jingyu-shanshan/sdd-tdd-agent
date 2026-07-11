from pathlib import Path

from sdd_tdd_agent.requirement_analysis import load_analysis_request


def test_should_load_typed_analysis_request_and_versioned_prompt(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (session / "requirement.md").write_text(
        "# Requirement\n\n## User request\n\nSupport PDF export\n",
        encoding="utf-8",
    )
    (workspace / "project.yml").write_text(
        "name: reports\ntarget_language: java\n",
        encoding="utf-8",
    )
    (workspace / "architecture.md").write_text(
        "# Architecture\n\nHexagonal architecture.\n",
        encoding="utf-8",
    )
    (workspace / "conventions.md").write_text(
        "# Conventions\n\nUse JUnit 5.\n",
        encoding="utf-8",
    )

    request = load_analysis_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert "Do not invent APIs" in request.prompt
    assert request.user_request == "Support PDF export"
    assert "name: reports" in request.project_metadata
    assert "Hexagonal architecture" in request.architecture
    assert "Use JUnit 5" in request.conventions
