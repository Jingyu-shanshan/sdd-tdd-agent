import json
from pathlib import Path

from sdd_tdd_agent.tdd_cycle import start_next_tdd_cycle
from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    TestGenerationRequest,
    render_test_plan,
)


def _case(test_id: str, task_id: str, dependencies: tuple[str, ...]) -> TestCasePlan:
    return TestCasePlan(
        test_id,
        task_id,
        "happy_path",
        f"Verify {test_id}",
        "Prove behavior.",
        f"src/{test_id.lower()}.test.ts",
        f"runs {test_id}",
        (),
        "Run it.",
        ("It works.",),
        dependencies,
    )


def test_should_clear_stale_production_source_for_new_cycle(tmp_path: Path) -> None:
    session = tmp_path / ".agent" / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (session / "tasks.md").write_text(
        "# Task Breakdown\n\n## Task T1: First\n\n## Task T2: Second\n",
        encoding="utf-8",
    )
    request = TestGenerationRequest("v1", "P", "R", "D", "T", "P", "A", "C")
    plan = GeneratedTestPlan(
        "Two cases.",
        (_case("TC1", "T1", ()), _case("TC2", "T2", ("TC1",))),
        (),
        (),
    )
    (session / "test-plan.md").write_text(
        render_test_plan(request, plan),
        encoding="utf-8",
    )
    state = {
        "session_id": "feature-1",
        "state": "IMPLEMENTATION",
        "current_task": "T1",
        "current_cycle": 1,
        "requirement_review": {"decision": "approved"},
        "design_review": {"decision": "approved"},
        "task_review": {"decision": "approved"},
        "tdd_cycle": {
            "current_test": "TC1",
            "phase": "GREEN",
            "completed_tests": ["TC1"],
        },
        "production_source": {
            "test_id": "TC1",
            "file_path": "src/first.ts",
            "sha256": "0" * 64,
        },
    }
    (session / "state.json").write_text(json.dumps(state), encoding="utf-8")

    start_next_tdd_cycle(tmp_path, "feature-1")

    updated = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert updated["tdd_cycle"]["current_test"] == "TC2"
    assert "production_source" not in updated
