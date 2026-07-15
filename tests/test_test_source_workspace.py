from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.test_generation import TestCasePlan
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    TestSourceGenerationRequest,
)
from sdd_tdd_agent.test_source_workspace import (
    MAX_SOURCE_FILES,
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


def _generated(
    content: str = "def test_should_export():\n    assert False\n",
) -> GeneratedTestSource:
    return GeneratedTestSource("TC1", "tests/test_export.py", content)


def test_should_collect_deterministic_bounded_visible_source_context(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "package.json").write_text('{"scripts": {"test": "vitest"}}')
    (tmp_path / "angular.json").write_text('{"projects": {}}')
    (tmp_path / "src" / "export.ts").write_text("export const run = () => 1;\n")
    (tmp_path / "src" / ".env").write_text("TOKEN=secret\n")
    (tmp_path / "src" / "blob.bin").write_bytes(b"\xff\x00")
    (tmp_path / "node_modules" / "dependency.ts").write_text("secret dependency")
    (tmp_path / "tests" / "test_export.py").write_text("# existing test\n")
    outside = tmp_path / "outside.ts"
    outside.write_text("outside\n")
    (tmp_path / "src" / "linked.ts").symlink_to(outside)

    snapshots = WorkspaceSourceCollector().collect(
        tmp_path,
        "tests/test_export.py",
    )

    assert tuple(snapshot.path for snapshot in snapshots) == (
        "angular.json",
        "package.json",
        "src/export.ts",
        "tests/test_export.py",
    )
    assert "TOKEN" not in "".join(snapshot.content for snapshot in snapshots)
    assert "outside" not in "".join(snapshot.content for snapshot in snapshots)


def test_should_reject_too_many_source_files(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    for index in range(MAX_SOURCE_FILES + 1):
        (source / f"source_{index:03}.ts").write_text("export {};\n")

    with pytest.raises(TestSourceWorkspaceError, match="too many"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/new.spec.ts")


def test_should_reject_non_utf8_visible_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "broken.ts").write_bytes(b"\xff\xfe")

    with pytest.raises(TestSourceWorkspaceError, match="UTF-8"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/new.spec.ts")


def test_should_reject_symlinked_target_ancestor_before_collection(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test_export.py").write_text("SECRET OUTSIDE\n")
    (tmp_path / "tests").symlink_to(outside, target_is_directory=True)

    with pytest.raises(TestSourceWorkspaceError, match="symbolic link"):
        WorkspaceSourceCollector().collect(tmp_path, "tests/test_export.py")


def test_should_atomically_create_planned_test_file(tmp_path: Path) -> None:
    writer = AtomicTestSourceWriter()

    result = writer.write(tmp_path, _request(), _generated())

    target = tmp_path / "tests" / "test_export.py"
    assert target.read_text() == _generated().content
    assert result.file_path == "tests/test_export.py"
    assert result.replaced_existing is False
    assert not (target.parent / ".test_export.py.agent.tmp").exists()


def test_should_replace_unchanged_snapshotted_test_file(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_export.py"
    target.parent.mkdir()
    target.write_text("# old\n")
    request = _request((SourceSnapshot("tests/test_export.py", "# old\n"),))

    result = AtomicTestSourceWriter().write(tmp_path, request, _generated())

    assert target.read_text() == _generated().content
    assert result.replaced_existing is True


@pytest.mark.parametrize("change", ["modify", "delete", "create"])
def test_should_reject_concurrent_target_change(
    tmp_path: Path,
    change: str,
) -> None:
    target = tmp_path / "tests" / "test_export.py"
    target.parent.mkdir()
    if change in {"modify", "delete"}:
        target.write_text("# captured\n")
        request = _request((SourceSnapshot("tests/test_export.py", "# captured\n"),))
        if change == "modify":
            target.write_text("# changed\n")
        else:
            target.unlink()
    else:
        request = _request()
        target.write_text("# created concurrently\n")
    before = target.read_text() if target.exists() else None

    with pytest.raises(TestSourceWorkspaceError, match="changed concurrently"):
        AtomicTestSourceWriter().write(tmp_path, request, _generated())

    assert (target.read_text() if target.exists() else None) == before


def test_should_reject_symlinked_destination_ancestor(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "tests").symlink_to(outside, target_is_directory=True)

    with pytest.raises(TestSourceWorkspaceError, match="symbolic link"):
        AtomicTestSourceWriter().write(tmp_path, _request(), _generated())

    assert not (outside / "test_export.py").exists()


def test_should_reject_existing_atomic_temporary_file(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    temporary = tests / ".test_export.py.agent.tmp"
    temporary.write_text("leftover\n")

    with pytest.raises(TestSourceWorkspaceError, match="temporary"):
        AtomicTestSourceWriter().write(tmp_path, _request(), _generated())

    assert temporary.read_text() == "leftover\n"
    assert not (tests / "test_export.py").exists()
