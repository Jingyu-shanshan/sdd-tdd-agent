from dataclasses import replace
from pathlib import Path

import pytest

from sdd_tdd_agent import design_generation as design
from tests.test_typescript_design_generation import (
    RecordingGenerator,
    _generic_proposal,
    _workspace,
)


MODULE_PATH = "src/reports/exporter.ts"


def _module(
    path: str = MODULE_PATH,
    exports: tuple[str, ...] = ("exportReport",),
) -> design.TypeScriptModuleDesign:
    return design.TypeScriptModuleDesign(path, "Export reports.", exports)


def _api(
    *,
    kind: str = "function",
    signature: str = "exportReport(): void",
) -> design.TypeScriptPublicApiDesign:
    return design.TypeScriptPublicApiDesign(
        "exportReport",
        kind,
        signature,
        MODULE_PATH,
    )


def _proposal(
    modules: tuple[design.TypeScriptModuleDesign, ...],
    apis: tuple[design.TypeScriptPublicApiDesign, ...] = (),
) -> design.DesignProposal:
    return replace(
        _generic_proposal(),
        typescript_modules=modules,
        public_apis=apis,
    )


@pytest.mark.parametrize(
    ("proposal", "message"),
    [
        (_proposal((_module(exports=()),)), "fields must not be blank"),
        (_proposal((_module(), _module())), "paths must be unique"),
        (_proposal((_module(),), (_api(), _api())), "identities must be unique"),
        (_proposal((_module(),), (_api(kind="namespace"),)), "kind is unsupported"),
        (_proposal((_module(),), (_api(signature=" "),)), "fields must not be blank"),
    ],
)
def test_should_reject_invalid_typed_design_records(
    tmp_path: Path,
    proposal: design.DesignProposal,
    message: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(ValueError, match=message):
        design.run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(proposal),
        )


def test_should_reject_typescript_records_for_generic_project(tmp_path: Path) -> None:
    _workspace(tmp_path)
    (tmp_path / "package.json").unlink()

    with pytest.raises(ValueError, match="Non-TypeScript"):
        design.run_design_generation(
            tmp_path,
            "feature-1",
            RecordingGenerator(_proposal((_module(),))),
        )
