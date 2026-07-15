import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Protocol, Set, Tuple


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "test_generation" / f"{PROMPT_VERSION}.md"
)
REQUIREMENT_HEADING = "# Requirement Analysis"
DESIGN_HEADING = "# Design Proposal"
TASK_HEADING = "# Task Breakdown"
TASK_ID_PATTERN = re.compile(
    r"^## Task ([A-Za-z][A-Za-z0-9_-]*):",
    re.MULTILINE,
)
PHASES = (
    "happy_path",
    "boundary",
    "exception",
    "integration",
    "regression",
)


@dataclass(frozen=True)
class TestGenerationRequest:
    """Typed approved context supplied to a test-plan generator."""

    __test__: ClassVar[bool] = False

    prompt_version: str
    prompt: str
    requirement: str
    design: str
    tasks: str
    project_metadata: str
    architecture: str
    conventions: str


@dataclass(frozen=True)
class TestCasePlan:
    """One ordered independently executable planned test."""

    __test__: ClassVar[bool] = False

    test_id: str
    task_id: str
    phase: str
    title: str
    objective: str
    test_file: str
    test_name: str
    preconditions: Tuple[str, ...]
    action: str
    expected_outcomes: Tuple[str, ...]
    dependencies: Tuple[str, ...]


@dataclass(frozen=True)
class GeneratedTestPlan:
    """Structured ordered test plan returned by a generator."""

    summary: str
    cases: Tuple[TestCasePlan, ...]
    risks: Tuple[str, ...]
    open_questions: Tuple[str, ...]


class TestPlanGenerator(Protocol):
    """Injectable boundary for a test-plan model adapter."""

    def generate(self, request: TestGenerationRequest) -> GeneratedTestPlan:
        """Generate a typed test plan without mutating project state."""
        ...


@dataclass(frozen=True)
class TestGenerationRun:
    """Result of a successful test-generation workflow run."""

    __test__: ClassVar[bool] = False

    session_id: str
    next_state: str
    plan: GeneratedTestPlan


def _validate_session_id(session_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError(f"Invalid session identifier: {session_id}")


def _extract_task_ids(tasks: str) -> Tuple[str, ...]:
    task_ids = tuple(TASK_ID_PATTERN.findall(tasks))
    if not task_ids:
        raise ValueError("Test generation requires generated tasks")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("Generated tasks contain duplicate identifiers")
    return task_ids


def load_test_generation_request(
    root: Path,
    session_id: str,
) -> TestGenerationRequest:
    """Load versioned approved context for one validated feature Session."""
    _validate_session_id(session_id)
    workspace = root / ".agent"
    session = workspace / "sessions" / session_id
    requirement = (session / "requirement.md").read_text(encoding="utf-8")
    design = (session / "design.md").read_text(encoding="utf-8")
    tasks = (session / "tasks.md").read_text(encoding="utf-8")
    if not requirement.strip() or not requirement.lstrip().startswith(
        REQUIREMENT_HEADING
    ):
        raise ValueError("Test generation requires analyzed requirements")
    if not design.strip() or not design.lstrip().startswith(DESIGN_HEADING):
        raise ValueError("Test generation requires a generated design")
    if not tasks.strip() or not tasks.lstrip().startswith(TASK_HEADING):
        raise ValueError("Test generation requires generated tasks")
    _extract_task_ids(tasks)
    return TestGenerationRequest(
        prompt_version=PROMPT_VERSION,
        prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        requirement=requirement,
        design=design,
        tasks=tasks,
        project_metadata=(workspace / "project.yml").read_text(encoding="utf-8"),
        architecture=(workspace / "architecture.md").read_text(encoding="utf-8"),
        conventions=(workspace / "conventions.md").read_text(encoding="utf-8"),
    )


def _render_items(items: Tuple[str, ...]) -> str:
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def _render_case(case: TestCasePlan) -> str:
    sections = (
        f"## Test {case.test_id}: {case.title}",
        "Status: pending",
        f"### Task\n\n{case.task_id}",
        f"### Phase\n\n{case.phase}",
        f"### Objective\n\n{case.objective}",
        f"### Test file\n\n`{case.test_file}`",
        f"### Test name\n\n`{case.test_name}`",
        f"### Preconditions\n\n{_render_items(case.preconditions)}",
        f"### Action\n\n{case.action}",
        f"### Expected outcomes\n\n{_render_items(case.expected_outcomes)}",
        f"### Dependencies\n\n{_render_items(case.dependencies)}",
    )
    return "\n\n".join(sections)


def render_test_plan(
    request: TestGenerationRequest,
    plan: GeneratedTestPlan,
) -> str:
    """Render a structured ordered test plan as deterministic Markdown."""
    case_sections = tuple(_render_case(case) for case in plan.cases)
    sections = (
        "# Test Generation Plan",
        f"Prompt version: `{request.prompt_version}`",
        f"## Summary\n\n{plan.summary}",
        *case_sections,
        f"## Risks\n\n{_render_items(plan.risks)}",
        f"## Open questions\n\n{_render_items(plan.open_questions)}",
    )
    return "\n\n".join(sections) + "\n"


def _validate_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Test {name} must not be empty")


def _validate_items(name: str, items: object, required: bool) -> None:
    if not isinstance(items, tuple):
        raise ValueError(f"Test {name} must be a tuple")
    if required and not items:
        raise ValueError(f"Test {name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"Test {name} must contain non-empty strings")


def _validate_test_file(test_file: object) -> None:
    _validate_text("file", test_file)
    if not isinstance(test_file, str):
        raise ValueError("Test file must be a string")
    normalized = test_file.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        "\0" in test_file
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:/", normalized) is not None
        or not path.parts
        or ".." in path.parts
    ):
        raise ValueError("Test file must be a safe relative path")


def _validate_case(
    case: TestCasePlan,
    task_ids: Set[str],
    preceding_ids: Set[str],
    previous_phase: int,
) -> int:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", case.test_id) is None:
        raise ValueError("Test identifier is invalid")
    if case.test_id in preceding_ids:
        raise ValueError(f"Duplicate test identifier: {case.test_id}")
    if case.task_id not in task_ids:
        raise ValueError("Test must reference an approved task")
    if case.phase not in PHASES:
        raise ValueError("Test phase is invalid")
    phase_rank = PHASES.index(case.phase)
    if phase_rank < previous_phase:
        raise ValueError("Test phases must not move backward")
    for name, value in (
        ("title", case.title),
        ("objective", case.objective),
        ("name", case.test_name),
        ("action", case.action),
    ):
        _validate_text(name, value)
    _validate_test_file(case.test_file)
    _validate_items("preconditions", case.preconditions, required=False)
    _validate_items("expected outcomes", case.expected_outcomes, required=True)
    _validate_items("dependencies", case.dependencies, required=False)
    if any(dependency not in preceding_ids for dependency in case.dependencies):
        raise ValueError("Test dependency must reference a preceding test")
    return phase_rank


def _validate_plan(plan: GeneratedTestPlan, task_ids: Tuple[str, ...]) -> None:
    _validate_text("plan summary", plan.summary)
    if not isinstance(plan.cases, tuple) or not plan.cases:
        raise ValueError("Test plan cases must not be empty")
    if not isinstance(plan.cases[0], TestCasePlan):
        raise ValueError("Test plan must contain TestCasePlan values")
    if plan.cases[0].phase != PHASES[0]:
        raise ValueError("Test plan must start with a happy-path case")
    preceding_ids: Set[str] = set()
    covered_tasks: Set[str] = set()
    previous_phase = 0
    approved_tasks = set(task_ids)
    for case in plan.cases:
        if not isinstance(case, TestCasePlan):
            raise ValueError("Test plan must contain TestCasePlan values")
        previous_phase = _validate_case(
            case,
            approved_tasks,
            preceding_ids,
            previous_phase,
        )
        preceding_ids.add(case.test_id)
        covered_tasks.add(case.task_id)
    if covered_tasks != approved_tasks:
        raise ValueError("Test plan must cover every approved task")
    _validate_items("risks", plan.risks, required=False)
    _validate_items("open questions", plan.open_questions, required=False)


def _is_approved(state: Dict[str, object], key: str) -> bool:
    review = state.get(key)
    return isinstance(review, dict) and review.get("decision") == "approved"


def _load_generation_state(state_path: Path, session_id: str) -> Dict[str, object]:
    state_value = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state_value, dict):
        raise ValueError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise ValueError("Session state identifier does not match Session")
    if state.get("state") != "TEST_GENERATION":
        raise ValueError("Test generation requires TEST_GENERATION state")
    for key, label in (
        ("requirement_review", "requirements"),
        ("design_review", "design"),
        ("task_review", "tasks"),
    ):
        if not _is_approved(state, key):
            raise ValueError(f"Test generation requires approved {label}")
    return state


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.test-plan.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def run_test_generation(
    root: Path,
    session_id: str,
    generator: TestPlanGenerator,
) -> TestGenerationRun:
    """Generate an ordered test plan and enter implementation readiness."""
    _validate_session_id(session_id)
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    state = _load_generation_state(state_path, session_id)
    request = load_test_generation_request(root, session_id)
    plan = generator.generate(request)
    if not isinstance(plan, GeneratedTestPlan):
        raise ValueError("Generator must return GeneratedTestPlan")
    _validate_plan(plan, _extract_task_ids(request.tasks))

    next_state = "IMPLEMENTATION"
    state["state"] = next_state
    rendered = render_test_plan(request, plan)
    serialized_state = f"{json.dumps(state, indent=2)}\n"
    _atomic_write(session / "test-plan.md", rendered)
    _atomic_write(state_path, serialized_state)
    return TestGenerationRun(
        session_id=session_id,
        next_state=next_state,
        plan=plan,
    )
