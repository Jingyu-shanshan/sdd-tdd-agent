from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.test_generation import TestCasePlan
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    MAX_SOURCE_BYTES,
    TestSourceGenerationRequest,
)
from sdd_tdd_agent.test_source_workspace import (
    MAX_SOURCE_CONTEXT_BYTES,
    AtomicTestSourceWriter,
    TestSourceWorkspaceError,
    WorkspaceSourceCollector,
)


def _request(sources: tuple[SourceSnapshot, ...] = ()) -> TestSourceGenerationRequest:
    current = TestCasePlan(
        "TC1",
        "T1",
        "happy_path",
        "Export",
        "Prove export.",
        "tests/test_export.py",
        "test_should_export",
        (),
        "Export.",
        ("It works.",),
        (),
    )
    return TestSourceGenerationRequest("v1", "P", "R", "D", current, sources)


def _generated() -> GeneratedTestSource:
    return GeneratedTestSource(
        "TC1",
        "tests/test_export.py",
        "def test_should_export():\n    assert False\n",
    )


@pytest.mark.parametrize("target", ["", "../secret.py", ".agent/state.json"])
def test_should_reject_unsafe_collection_target(
    tmp_path: Path,
    target: str,
) -> None:
    with pytest.raises(TestSourceWorkspaceError, match="safe relative path"):
        WorkspaceSourceCollector().collect(tmp_path, target)


def test_should_reject_empty_visible_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "empty.ts").write_text("\n")

    with pytest.raises(TestSourceWorkspaceError, match="empty"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/new.spec.ts")


def test_should_reject_oversized_visible_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "large.ts").write_text("x" * (MAX_SOURCE_BYTES + 1))

    with pytest.raises(TestSourceWorkspaceError, match="too large"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/new.spec.ts")


def test_should_reject_oversized_total_source_context(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    size = (MAX_SOURCE_CONTEXT_BYTES // 3) + 1
    for index in range(3):
        (source / f"large_{index}.ts").write_text("x" * size)

    with pytest.raises(TestSourceWorkspaceError, match="context is too large"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/new.spec.ts")


def test_should_reject_direct_symlink_destination(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("outside\n")
    (tests / "test_export.py").symlink_to(outside)

    with pytest.raises(TestSourceWorkspaceError, match="symbolic link"):
        AtomicTestSourceWriter().write(tmp_path, _request(), _generated())

    assert outside.read_text() == "outside\n"


def test_should_reject_non_utf8_target_during_concurrency_check(
    tmp_path: Path,
) -> None:
    target = tmp_path / "tests" / "test_export.py"
    target.parent.mkdir()
    target.write_bytes(b"\xff\xfe")
    request = _request((SourceSnapshot("tests/test_export.py", "captured\n"),))

    with pytest.raises(TestSourceWorkspaceError, match="could not be verified"):
        AtomicTestSourceWriter().write(tmp_path, request, _generated())
