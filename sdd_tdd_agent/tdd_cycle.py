import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from sdd_tdd_agent.test_generation import (
    GeneratedTestPlan,
    TestCasePlan,
    _extract_task_ids,
    _validate_plan,
)


PLAN_HEADING = "# Test Generation Plan"
CASE_PATTERN = re.compile(
    r"^## Test ([A-Za-z][A-Za-z0-9_-]*): ([^\n]+)\n\n"
    r"(.*?)(?=^## Test |^## Risks\n|\Z)",
    re.MULTILINE | re.DOTALL,
)
SECTION_PATTERN = re.compile(
    r"^### ([^\n]+)\n\n(.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)
CASE_SECTIONS = {
    "Task",
    "Phase",
    "Objective",
    "Test file",
    "Test name",
    "Preconditions",
    "Action",
    "Expected outcomes",
    "Dependencies",
}
PROGRESS_FIELDS = {"current_test", "phase", "completed_tests"}
TDD_PHASES = {"WRITE_TEST", "RED", "IMPLEMENT", "GREEN"}


@dataclass(frozen=True)
class SourceSnapshot:
    """One explicit production source visible to a blind developer context."""

    path: str
    content: str


@dataclass(frozen=True)
class BlindDevelopmentContext:
    """Restricted context for implementing only the current failing test."""

    current_test: TestCasePlan
    production_sources: Tuple[SourceSnapshot, ...]
    compile_output: str
    test_output: str
    current_test_source: Optional[SourceSnapshot] = None


@dataclass(frozen=True)
class TddCycleStart:
    """Result of atomically selecting and starting one test cycle."""

    session_id: str
    cycle_number: int
    test_case: TestCasePlan


@dataclass(frozen=True)
class _CycleContext:
    session_path: Path
    state: Dict[str, object]
    cases: Tuple[TestCasePlan, ...]
    completed_tests: Tuple[str, ...]
    active_phase: Optional[str]


def _parse_items(value: str, field: str) -> Tuple[str, ...]:
    normalized = value.strip()
    if normalized == "- None identified.":
        return ()
    lines = normalized.splitlines()
    if not lines or any(not line.startswith("- ") for line in lines):
        raise ValueError(f"Generated test {field} list is invalid")
    items = tuple(line[2:] for line in lines)
    if any(not item.strip() for item in items):
        raise ValueError(f"Generated test {field} list is invalid")
    return items


def _parse_code_value(value: str, field: str) -> str:
    normalized = value.strip()
    if (
        len(normalized) < 3
        or not normalized.startswith("`")
        or not normalized.endswith("`")
    ):
        raise ValueError(f"Generated test {field} is invalid")
    return normalized[1:-1]


def _parse_case(match: re.Match[str]) -> TestCasePlan:
    test_id, title, body = match.groups()
    if not body.startswith("Status: pending\n\n"):
        raise ValueError("Generated test status is invalid")
    sections = dict(SECTION_PATTERN.findall(body))
    if set(sections) != CASE_SECTIONS:
        raise ValueError("Generated test sections do not match schema")
    return TestCasePlan(
        test_id=test_id,
        task_id=sections["Task"].strip(),
        phase=sections["Phase"].strip(),
        title=title.strip(),
        objective=sections["Objective"].strip(),
        test_file=_parse_code_value(sections["Test file"], "file"),
        test_name=_parse_code_value(sections["Test name"], "name"),
        preconditions=_parse_items(sections["Preconditions"], "preconditions"),
        action=sections["Action"].strip(),
        expected_outcomes=_parse_items(
            sections["Expected outcomes"],
            "expected outcomes",
        ),
        dependencies=_parse_items(sections["Dependencies"], "dependencies"),
    )


def _parse_cases(
    plan_content: str, task_ids: Tuple[str, ...]
) -> Tuple[TestCasePlan, ...]:
    if not plan_content.lstrip().startswith(PLAN_HEADING):
        raise ValueError("TDD cycle requires a generated test plan")
    matches = tuple(CASE_PATTERN.finditer(plan_content))
    if not matches:
        raise ValueError("Generated test plan contains no cases")
    cases = tuple(_parse_case(match) for match in matches)
    parsed_plan = GeneratedTestPlan("Validated generated plan", cases, (), ())
    _validate_plan(parsed_plan, task_ids)
    return cases


def _has_approval(state: Dict[str, object], key: str) -> bool:
    value = state.get(key)
    return isinstance(value, dict) and value.get("decision") == "approved"


def _validate_progress(
    value: object,
    case_ids: Tuple[str, ...],
) -> Tuple[Tuple[str, ...], Optional[str]]:
    if value is None:
        return (), None
    if not isinstance(value, dict) or set(value) != PROGRESS_FIELDS:
        raise ValueError("TDD cycle progress is invalid")
    current_test = value["current_test"]
    phase = value["phase"]
    completed_value = value["completed_tests"]
    if (
        not isinstance(current_test, str)
        or current_test not in case_ids
        or not isinstance(phase, str)
        or phase not in TDD_PHASES
        or not isinstance(completed_value, list)
        or any(not isinstance(item, str) for item in completed_value)
    ):
        raise ValueError("TDD cycle progress is invalid")
    completed = tuple(completed_value)
    if completed != case_ids[: len(completed)]:
        raise ValueError("Completed tests must follow plan order")
    if phase == "GREEN" and (not completed or current_test != completed[-1]):
        raise ValueError("GREEN cycle must record its completed current test")
    if phase != "GREEN" and current_test in completed:
        raise ValueError("Active test cannot already be completed")
    return completed, phase


def _load_cycle_context(root: Path, session_id: str) -> _CycleContext:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError("Invalid Session identifier")
    session = root / ".agent" / "sessions" / session_id
    state_value = json.loads((session / "state.json").read_text(encoding="utf-8"))
    if not isinstance(state_value, dict):
        raise ValueError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise ValueError("Session state identifier does not match Session")
    if state.get("state") != "IMPLEMENTATION":
        raise ValueError("TDD cycle requires IMPLEMENTATION state")
    for key in ("requirement_review", "design_review", "task_review"):
        if not _has_approval(state, key):
            raise ValueError("TDD cycle requires all prior approvals")
    tasks = (session / "tasks.md").read_text(encoding="utf-8")
    plan = (session / "test-plan.md").read_text(encoding="utf-8")
    cases = _parse_cases(plan, _extract_task_ids(tasks))
    case_ids = tuple(case.test_id for case in cases)
    completed, phase = _validate_progress(state.get("tdd_cycle"), case_ids)
    return _CycleContext(session, state, cases, completed, phase)


def _next_case(context: _CycleContext) -> Optional[TestCasePlan]:
    completed: Set[str] = set(context.completed_tests)
    for case in context.cases:
        if case.test_id in completed:
            continue
        if any(dependency not in completed for dependency in case.dependencies):
            raise ValueError("Next test dependencies are not complete")
        return case
    return None


def _current_case(context: _CycleContext) -> TestCasePlan:
    progress = context.state.get("tdd_cycle")
    if not isinstance(progress, dict):
        raise ValueError("TDD cycle progress is invalid")
    current_test = progress.get("current_test")
    for case in context.cases:
        if case.test_id == current_test:
            return case
    raise ValueError("Current TDD test does not exist in generated plan")


def _cycle_number(state: Dict[str, object]) -> int:
    value = state.get("current_cycle", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Session cycle number is invalid")
    return value


def _start_cycle(context: _CycleContext) -> TddCycleStart:
    session_id = context.state.get("session_id")
    if not isinstance(session_id, str):
        raise ValueError("Session state identifier is invalid")
    test_case = _next_case(context)
    if test_case is None:
        raise ValueError("All planned tests are complete")
    cycle_number = _cycle_number(context.state) + 1
    context.state["current_task"] = test_case.task_id
    context.state["current_cycle"] = cycle_number
    context.state["tdd_cycle"] = {
        "current_test": test_case.test_id,
        "phase": "WRITE_TEST",
        "completed_tests": list(context.completed_tests),
    }
    context.state.pop("test_source", None)
    context.state.pop("red_evidence", None)
    context.state.pop("production_source", None)
    serialized = f"{json.dumps(context.state, indent=2)}\n"
    state_path = context.session_path / "state.json"
    temporary = context.session_path / ".state.json.tdd-cycle.tmp"
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(state_path)
    return TddCycleStart(
        session_id,
        cycle_number,
        test_case,
    )


def select_next_test_case(root: Path, session_id: str) -> Optional[TestCasePlan]:
    """Read and select the next incomplete generated test without mutation."""
    return _next_case(_load_cycle_context(root, session_id))


def load_current_test_case(
    root: Path,
    session_id: str,
    expected_phase: str,
) -> TestCasePlan:
    """Load the active current test only when it is in the expected TDD phase."""
    if expected_phase not in TDD_PHASES:
        raise ValueError("Expected TDD phase is invalid")
    context = _load_cycle_context(root, session_id)
    if context.active_phase != expected_phase:
        raise ValueError(f"Current TDD cycle must be in {expected_phase} phase")
    return _current_case(context)


def load_current_tdd_phase(root: Path, session_id: str) -> Optional[str]:
    """Load the validated active TDD phase, or None before a cycle starts."""
    return _load_cycle_context(root, session_id).active_phase


def prepare_write_test_cycle(root: Path, session_id: str) -> TddCycleStart:
    """Resume WRITE_TEST or atomically start the next eligible test cycle."""
    context = _load_cycle_context(root, session_id)
    if context.active_phase == "WRITE_TEST":
        return TddCycleStart(
            session_id,
            _cycle_number(context.state),
            _current_case(context),
        )
    if context.active_phase is not None and context.active_phase != "GREEN":
        raise ValueError("A TDD cycle is already active")
    return _start_cycle(context)


def start_next_tdd_cycle(root: Path, session_id: str) -> TddCycleStart:
    """Atomically start exactly one planned test-writing cycle."""
    context = _load_cycle_context(root, session_id)
    if context.active_phase is not None and context.active_phase != "GREEN":
        raise ValueError("A TDD cycle is already active")
    return _start_cycle(context)
