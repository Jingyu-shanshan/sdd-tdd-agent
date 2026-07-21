import io
from pathlib import Path

from sdd_tdd_agent.cli import main
from sdd_tdd_agent.ecosystem_registry import (
    EcosystemCapability,
    list_ecosystems,
    render_ecosystems,
)


def test_should_list_only_documented_supported_ecosystems() -> None:
    ecosystems = list_ecosystems()

    assert ecosystems == (
        EcosystemCapability(
            language="java",
            status="supported",
            tools=("maven", "gradle"),
            test_frameworks=("junit5",),
        ),
        EcosystemCapability(
            language="typescript",
            status="supported",
            tools=("npm", "pnpm", "yarn"),
            test_frameworks=("jest", "vitest", "angular"),
        ),
    )


def test_should_render_deterministic_ecosystem_matrix() -> None:
    assert render_ecosystems(list_ecosystems()) == (
        "java: supported\n"
        "  tools: maven, gradle\n"
        "  test frameworks: junit5\n"
        "typescript: supported\n"
        "  tools: npm, pnpm, yarn\n"
        "  test frameworks: jest, vitest, angular\n"
    )


def test_should_list_ecosystems_without_project_side_effects(tmp_path: Path) -> None:
    output = io.StringIO()
    error_output = io.StringIO()

    exit_code = main(
        ["ecosystem", "list"],
        out=output,
        err=error_output,
        root=tmp_path,
    )

    assert exit_code == 0
    assert output.getvalue() == render_ecosystems(list_ecosystems())
    assert error_output.getvalue() == ""
    assert not (tmp_path / ".agent").exists()
