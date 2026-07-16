import json
import hashlib
from pathlib import Path
from typing import Tuple, cast

import pytest

from sdd_tdd_agent.production_source_generation import (
    MAX_PRODUCTION_SOURCE_BYTES,
    GeneratedProductionSource,
    ProductionSourceGenerationRequest,
    load_production_source_generation_request,
    validate_generated_production_source,
)
from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.production_source_workspace import (
    WorkspaceProductionSourceCollector,
)
from tests.production_source_support import (
    GENERATED_CONTENT,
    PRODUCTION_CONTENT,
    TEST_CONTENT,
    create_red_workspace,
)


def _request(root: Path) -> ProductionSourceGenerationRequest:
    sources = WorkspaceProductionSourceCollector().collect(root)
    return load_production_source_generation_request(root, "feature-1", sources)


def test_should_load_only_digest_bound_blind_development_context(
    tmp_path: Path,
) -> None:
    create_red_workspace(tmp_path)

    request = _request(tmp_path)

    context = request.context
    assert request.prompt_version == "v1"
    assert context.current_test.test_id == "TC1"
    assert context.current_test_source is not None
    assert context.current_test_source.path == "src/export.test.ts"
    assert context.current_test_source.content == TEST_CONTENT
    assert context.production_sources == (
        type(context.production_sources[0])("src/export.ts", PRODUCTION_CONTENT),
    )
    assert context.test_output == "src/export.test.ts: exports report failed\n"
    assert context.compile_output == ""
    for forbidden in ("requirement", "design", "tasks", "test_plan", "future_tests"):
        assert not hasattr(context, forbidden)
        assert not hasattr(request, forbidden)


def test_should_reject_test_source_changed_after_red(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    (tmp_path / "src" / "export.test.ts").write_text(
        "test('changed', () => {})\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="changed"):
        _request(tmp_path)


def test_should_reject_unsanitized_persisted_red_evidence(tmp_path: Path) -> None:
    session = create_red_workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["red_evidence"]["stdout"] = "src/export.test.ts token=SECRET"
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="sanitized"):
        _request(tmp_path)


@pytest.mark.parametrize(
    "evidence",
    [
        {},
        {
            "test_id": "TC1",
            "file_path": "src/export.test.ts",
            "command": [],
            "returncode": 0,
            "stdout": "src/export.test.ts failed",
            "stderr": "",
        },
        {
            "test_id": "TC1",
            "file_path": "src/export.test.ts",
            "command": ["npm"],
            "returncode": 1,
            "stdout": "x" * 16_001,
            "stderr": "",
        },
    ],
)
def test_should_reject_invalid_red_evidence(
    tmp_path: Path,
    evidence: object,
) -> None:
    session = create_red_workspace(tmp_path)
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["red_evidence"] = evidence
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="RED evidence"):
        _request(tmp_path)


@pytest.mark.parametrize("content", ["", "x" * (MAX_PRODUCTION_SOURCE_BYTES + 1)])
def test_should_reject_empty_or_oversized_current_test_source(
    tmp_path: Path,
    content: str,
) -> None:
    session = create_red_workspace(tmp_path)
    target = tmp_path / "src" / "export.test.ts"
    target.write_text(content, encoding="utf-8")
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    state["test_source"]["sha256"] = hashlib.sha256(content.encode()).hexdigest()
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="test source"):
        _request(tmp_path)


@pytest.mark.parametrize(
    "sources",
    [
        cast(Tuple[SourceSnapshot, ...], ["invalid"]),
        (SourceSnapshot("src/empty.ts", ""),),
        (
            SourceSnapshot("src/duplicate.ts", "one"),
            SourceSnapshot("src/duplicate.ts", "two"),
        ),
        (SourceSnapshot("src/large.ts", "x" * (MAX_PRODUCTION_SOURCE_BYTES + 1)),),
        (
            SourceSnapshot("src/a.ts", "x" * 700_000),
            SourceSnapshot("src/b.ts", "x" * 700_000),
            SourceSnapshot("src/c.ts", "x" * 700_000),
        ),
    ],
)
def test_should_reject_invalid_production_source_context(
    tmp_path: Path,
    sources: Tuple[SourceSnapshot, ...],
) -> None:
    create_red_workspace(tmp_path)

    with pytest.raises(ValueError, match="Production source"):
        load_production_source_generation_request(tmp_path, "feature-1", sources)


def test_should_validate_one_current_minimal_production_source(
    tmp_path: Path,
) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    generated = GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT)

    assert validate_generated_production_source(request, generated) == generated


@pytest.mark.parametrize(
    "file_path",
    [
        "../outside.ts",
        ".agent/state.py",
        "package.json",
        "src/export.test.ts",
        "src/export.spec.ts",
        "src/test/helper.ts",
        "src/.hidden.ts",
        "src/config.json",
        "src\\export.ts",
    ],
)
def test_should_reject_nonproduction_generated_target(
    tmp_path: Path,
    file_path: str,
) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)

    with pytest.raises(ValueError, match="production source path"):
        validate_generated_production_source(
            request,
            GeneratedProductionSource("TC1", file_path, GENERATED_CONTENT),
        )


@pytest.mark.parametrize(
    "generated",
    [
        GeneratedProductionSource("TC2", "src/export.ts", GENERATED_CONTENT),
        GeneratedProductionSource("TC1", "src/export.ts", ""),
        GeneratedProductionSource("TC1", "src/export.ts", "source\0content"),
        GeneratedProductionSource("TC1", "src/export.ts", "\ud800"),
        GeneratedProductionSource(
            "TC1",
            "src/export.ts",
            "x" * (MAX_PRODUCTION_SOURCE_BYTES + 1),
        ),
    ],
)
def test_should_reject_invalid_generated_production_source(
    tmp_path: Path,
    generated: GeneratedProductionSource,
) -> None:
    create_red_workspace(tmp_path)

    with pytest.raises(ValueError):
        validate_generated_production_source(_request(tmp_path), generated)


def test_should_reject_wrong_request_or_result_types(tmp_path: Path) -> None:
    create_red_workspace(tmp_path)
    request = _request(tmp_path)
    generated = GeneratedProductionSource("TC1", "src/export.ts", GENERATED_CONTENT)

    with pytest.raises(ValueError, match="request"):
        validate_generated_production_source(
            cast(ProductionSourceGenerationRequest, object()),
            generated,
        )
    with pytest.raises(ValueError, match="result"):
        validate_generated_production_source(
            request,
            cast(GeneratedProductionSource, object()),
        )
