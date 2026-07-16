from pathlib import Path

import pytest

from sdd_tdd_agent.production_source_generation import (
    GeneratedProductionSource,
    ProductionSourceGenerationRequest,
    load_production_source_generation_request,
)
from sdd_tdd_agent.production_source_workspace import (
    MAX_PRODUCTION_SOURCE_FILES,
    AtomicProductionSourceWriter,
    ProductionSourceWorkspaceError,
    WorkspaceProductionSourceCollector,
)
from tests.production_source_support import (
    GENERATED_CONTENT,
    create_red_workspace,
)


def _request(root: Path) -> ProductionSourceGenerationRequest:
    sources = WorkspaceProductionSourceCollector().collect(root)
    return load_production_source_generation_request(root, "feature-1", sources)


def test_should_collect_only_visible_production_source(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    source = tmp_path / "src"
    (source / "other.spec.ts").write_text("test('other', () => {})")
    (source / ".hidden.ts").write_text("export const hidden = true")
    tests = source / "test"
    tests.mkdir()
    (tests / "helper.ts").write_text("export const helper = true")
    outside = tmp_path / "outside.ts"
    outside.write_text("outside")
    (source / "linked.ts").symlink_to(outside)

    snapshots = WorkspaceProductionSourceCollector().collect(tmp_path)

    assert tuple(item.path for item in snapshots) == ("src/export.ts",)


def test_should_return_empty_context_without_source_root(tmp_path: Path) -> None:
    assert WorkspaceProductionSourceCollector().collect(tmp_path) == ()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "empty"),
        ("x" * 1_000_001, "too large"),
    ],
)
def test_should_reject_invalid_visible_production_source(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "export.ts").write_text(content)

    with pytest.raises(ProductionSourceWorkspaceError, match=message):
        WorkspaceProductionSourceCollector().collect(tmp_path)


def test_should_reject_too_many_production_sources(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    for index in range(MAX_PRODUCTION_SOURCE_FILES + 1):
        (source / f"source_{index}.ts").write_text("export {}\n")

    with pytest.raises(ProductionSourceWorkspaceError, match="too many"):
        WorkspaceProductionSourceCollector().collect(tmp_path)


def test_should_reject_oversized_total_production_context(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    for name in ("a.ts", "b.ts", "c.ts"):
        (source / name).write_text("x" * 700_000)

    with pytest.raises(ProductionSourceWorkspaceError, match="context is too large"):
        WorkspaceProductionSourceCollector().collect(tmp_path)


def test_should_atomically_replace_unchanged_captured_production_source(
    tmp_path: Path,
) -> None:
    create_red_workspace(tmp_path)

    result = AtomicProductionSourceWriter().write(
        tmp_path,
        _request(tmp_path),
        GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT),
    )

    assert result.file_path == "src/export.ts"
    assert result.replaced_existing is True
    assert (tmp_path / "src" / "export.ts").read_text() == GENERATED_CONTENT


def test_should_atomically_create_one_new_production_source(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)

    result = AtomicProductionSourceWriter().write(
        tmp_path,
        _request(tmp_path),
        GeneratedProductionSource(
            "TC1",
            "src/report.ts",
            "export const report = 'report'\n",
        ),
    )

    assert result.replaced_existing is False
    assert (tmp_path / "src" / "report.ts").read_text() == (
        "export const report = 'report'\n"
    )


def test_should_reject_existing_target_changed_after_capture(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    target = tmp_path / "src" / "export.ts"
    target.write_text("export const changed = true\n")

    with pytest.raises(ProductionSourceWorkspaceError, match="changed concurrently"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            request,
            GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT),
        )

    assert target.read_text() == "export const changed = true\n"


def test_should_reject_unexpected_existing_new_target(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    target = tmp_path / "src" / "report.ts"
    target.write_text("concurrent\n")

    with pytest.raises(ProductionSourceWorkspaceError, match="changed concurrently"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            request,
            GeneratedProductionSource("TC1", "src/report.ts", "generated\n"),
        )

    assert target.read_text() == "concurrent\n"


def test_should_reject_captured_target_removed_before_write(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    target = tmp_path / "src" / "export.ts"
    target.unlink()

    with pytest.raises(ProductionSourceWorkspaceError, match="changed concurrently"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            request,
            GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT),
        )


def test_should_reject_non_utf8_target_during_write_check(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    target = tmp_path / "src" / "export.ts"
    target.write_bytes(b"\xff\xfe")

    with pytest.raises(ProductionSourceWorkspaceError, match="could not be verified"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            request,
            GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT),
        )


def test_should_reject_parent_path_that_became_file(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    parent = tmp_path / "src" / "new"
    parent.write_text("not a directory")

    with pytest.raises(ProductionSourceWorkspaceError, match="could not be prepared"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            _request(tmp_path),
            GeneratedProductionSource("TC1", "src/new/report.ts", "generated\n"),
        )


def test_should_reject_production_source_symlink_target(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    outside = tmp_path / "outside.ts"
    outside.write_text("outside\n")
    target = tmp_path / "src" / "report.ts"
    target.symlink_to(outside)

    with pytest.raises(ProductionSourceWorkspaceError, match="symbolic link"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            _request(tmp_path),
            GeneratedProductionSource("TC1", "src/report.ts", "generated\n"),
        )

    assert outside.read_text() == "outside\n"


def test_should_reject_atomic_temporary_collision(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    temporary = tmp_path / "src" / ".export.ts.agent.tmp"
    temporary.write_text("occupied\n")

    with pytest.raises(ProductionSourceWorkspaceError, match="temporary"):
        AtomicProductionSourceWriter().write(
            tmp_path,
            _request(tmp_path),
            GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT),
        )

    assert temporary.read_text() == "occupied\n"
