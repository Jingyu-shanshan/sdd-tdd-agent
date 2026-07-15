import json
from pathlib import Path

import pytest

from sdd_tdd_agent.tdd_cycle import SourceSnapshot
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)
from sdd_tdd_agent.test_source_generation import (
    GeneratedTestSource,
    MAX_SOURCE_BYTES,
    load_test_source_generation_request,
    validate_generated_test_source,
)


def _case() -> TestCasePlan:
    return TestCasePlan(
        test_id="TC1",
        task_id="T1",
        phase="happy_path",
        title="Export a report",
        objective="Prove one report can be exported.",
        test_file="tests/test_export.py",
        test_name="test_should_export_report",
        preconditions=("A report exists.",),
        action="Export the report.",
        expected_outcomes=("A PDF is returned.",),
        dependencies=(),
    )


def _workspace(root: Path, phase: str = "WRITE_TEST") -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    (workspace / "architecture.md").write_text(
        "# Architecture\n",
        encoding="utf-8",
    )
    (workspace / "conventions.md").write_text(
        "# Conventions\n",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\nApproved requirement.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(
        "# Design Proposal\n\nApproved design.\n",
        encoding="utf-8",
    )
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: Export\n",
        encoding="utf-8",
    )
    plan_request = TestGenerationRequest(
        "v1", "Prompt", "Req", "Design", "Tasks", "P", "A", "C"
    )
    plan = GeneratedTestPlan("One case.", (_case(),), (), ())
    (session / "test-plan.md").write_text(
        render_test_plan(plan_request, plan),
        encoding="utf-8",
    )
    completed_tests = ["TC1"] if phase == "GREEN" else []
    state = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
        "current_task": "T1",
        "current_cycle": 1,
        "tdd_cycle": {
            "current_test": "TC1",
            "phase": phase,
            "completed_tests": completed_tests,
        },
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return session


def test_should_load_isolated_current_test_author_context(tmp_path: Path) -> None:
    session = _workspace(tmp_path)
    before = {path.name: path.read_text(encoding="utf-8") for path in session.iterdir()}
    sources = (
        SourceSnapshot("src/export.py", "def export_report(): ...\n"),
        SourceSnapshot("tests/test_export.py", "# existing tests\n"),
    )

    request = load_test_source_generation_request(tmp_path, "feature-1", sources)

    assert request.prompt_version == "v1"
    assert "exactly one" in request.prompt.lower()
    assert request.requirement.startswith("# Requirement Analysis")
    assert request.design.startswith("# Design Proposal")
    assert request.current_test == _case()
    assert request.sources == sources
    assert not hasattr(request, "tasks")
    assert not hasattr(request, "test_plan")
    assert not hasattr(request, "future_tests")
    assert not hasattr(request, "compile_output")
    assert not hasattr(request, "test_output")
    assert {
        path.name: path.read_text(encoding="utf-8") for path in session.iterdir()
    } == before


@pytest.mark.parametrize("phase", ["RED", "IMPLEMENT", "GREEN"])
def test_should_require_write_test_phase(tmp_path: Path, phase: str) -> None:
    _workspace(tmp_path, phase)

    with pytest.raises(ValueError, match="WRITE_TEST"):
        load_test_source_generation_request(tmp_path, "feature-1", ())


@pytest.mark.parametrize(
    ("sources", "message"),
    [
        ([SourceSnapshot("src/export.py", "code")], "tuple"),
        (("src/export.py",), "SourceSnapshot"),
        ((SourceSnapshot("../secret", "code"),), "safe relative path"),
        ((SourceSnapshot("/tmp/source.py", "code"),), "safe relative path"),
        ((SourceSnapshot(".agent/project.yml", "code"),), "protected"),
        ((SourceSnapshot(".git/config", "code"),), "protected"),
        ((SourceSnapshot("src/export.py", ""),), "must not be empty"),
        ((SourceSnapshot("src/export.py", "bad\x00code"),), "null bytes"),
        ((SourceSnapshot("src/export.py", "x" * (MAX_SOURCE_BYTES + 1)),), "large"),
        (
            (
                SourceSnapshot("src/export.py", "one"),
                SourceSnapshot("src/export.py", "two"),
            ),
            "duplicate",
        ),
    ],
)
def test_should_reject_invalid_source_context(
    tmp_path: Path,
    sources: object,
    message: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(ValueError, match=message):
        load_test_source_generation_request(tmp_path, "feature-1", sources)  # type: ignore[arg-type]


def test_should_validate_source_bound_to_current_planned_test(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_test_source_generation_request(tmp_path, "feature-1", ())
    generated = GeneratedTestSource(
        test_id="TC1",
        file_path="tests/test_export.py",
        content="def test_should_export_report():\n    assert False\n",
    )

    assert validate_generated_test_source(request, generated) == generated


@pytest.mark.parametrize(
    ("generated", "message"),
    [
        (
            GeneratedTestSource("TC2", "tests/test_export.py", "test"),
            "test identifier",
        ),
        (GeneratedTestSource("TC1", "tests/other.py", "test"), "file path"),
        (GeneratedTestSource("TC1", "tests/test_export.py", ""), "empty"),
        (
            GeneratedTestSource("TC1", "tests/test_export.py", "bad\x00code"),
            "null bytes",
        ),
        (
            GeneratedTestSource(
                "TC1",
                "tests/test_export.py",
                "x" * (MAX_SOURCE_BYTES + 1),
            ),
            "large",
        ),
    ],
)
def test_should_reject_generated_source_outside_current_case(
    tmp_path: Path,
    generated: GeneratedTestSource,
    message: str,
) -> None:
    _workspace(tmp_path)
    request = load_test_source_generation_request(tmp_path, "feature-1", ())

    with pytest.raises(ValueError, match=message):
        validate_generated_test_source(request, generated)


def test_should_reject_non_generated_source_result(tmp_path: Path) -> None:
    _workspace(tmp_path)
    request = load_test_source_generation_request(tmp_path, "feature-1", ())

    with pytest.raises(ValueError, match="GeneratedTestSource"):
        validate_generated_test_source(request, object())  # type: ignore[arg-type]
