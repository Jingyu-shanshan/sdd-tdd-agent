import io
from pathlib import Path

import pytest

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.project_memory import (
    MAX_PROJECT_MEMORY_BYTES,
    ProjectMemoryError,
    load_project_memory,
    render_project_memory,
)


def _initialized(root: Path) -> Path:
    initialize_project(root)
    return root / ".agent"


def test_should_load_and_render_existing_project_memory(tmp_path: Path) -> None:
    workspace = _initialized(tmp_path)

    memory = load_project_memory(tmp_path)

    assert memory.project_metadata == (workspace / "project.yml").read_text()
    assert memory.architecture == (workspace / "architecture.md").read_text()
    assert memory.conventions == (workspace / "conventions.md").read_text()
    assert len(memory.digest) == 64
    assert render_project_memory(memory) == (
        "Project memory: ready\n"
        f"Digest: {memory.digest}\n"
        f"- project.yml: {len(memory.project_metadata.encode())} bytes\n"
        f"- architecture.md: {len(memory.architecture.encode())} bytes\n"
        f"- conventions.md: {len(memory.conventions.encode())} bytes\n"
    )


def test_should_change_digest_when_reviewed_memory_changes(tmp_path: Path) -> None:
    workspace = _initialized(tmp_path)
    initial = load_project_memory(tmp_path)

    (workspace / "architecture.md").write_text(
        "# Architecture\n\nUse ports and adapters.\n",
        encoding="utf-8",
    )

    assert load_project_memory(tmp_path).digest != initial.digest


@pytest.mark.parametrize(
    "filename", ["project.yml", "architecture.md", "conventions.md"]
)
def test_should_reject_empty_memory(
    tmp_path: Path,
    filename: str,
) -> None:
    workspace = _initialized(tmp_path)
    (workspace / filename).write_text("", encoding="utf-8")

    with pytest.raises(ProjectMemoryError, match="invalid"):
        load_project_memory(tmp_path)


def test_should_reject_missing_or_non_utf8_memory(tmp_path: Path) -> None:
    workspace = _initialized(tmp_path)
    (workspace / "project.yml").unlink()

    with pytest.raises(ProjectMemoryError, match="invalid"):
        load_project_memory(tmp_path)

    _initialized(tmp_path)
    (workspace / "project.yml").write_bytes(b"\xff")

    with pytest.raises(ProjectMemoryError, match="invalid"):
        load_project_memory(tmp_path)


def test_should_reject_oversized_memory(tmp_path: Path) -> None:
    workspace = _initialized(tmp_path)
    (workspace / "architecture.md").write_text(
        "x" * MAX_PROJECT_MEMORY_BYTES,
        encoding="utf-8",
    )

    with pytest.raises(ProjectMemoryError, match="too large"):
        load_project_memory(tmp_path)


def test_should_reject_symlinked_memory(tmp_path: Path) -> None:
    workspace = _initialized(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Secret\n", encoding="utf-8")
    architecture = workspace / "architecture.md"
    architecture.unlink()
    architecture.symlink_to(outside)

    with pytest.raises(ProjectMemoryError, match="unsafe"):
        load_project_memory(tmp_path)


def test_should_render_project_memory_through_cli(tmp_path: Path) -> None:
    _initialized(tmp_path)
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(["memory"], out=output, err=error_output, root=tmp_path)

    assert exit_code == 0
    assert output.getvalue().startswith("Project memory: ready\nDigest: ")
    assert error_output.getvalue() == ""


def test_should_report_invalid_memory_through_cli(tmp_path: Path) -> None:
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(["memory"], out=output, err=error_output, root=tmp_path)

    assert exit_code == 2
    assert output.getvalue() == ""
    assert error_output.getvalue() == "Error: Project memory file is invalid\n"
