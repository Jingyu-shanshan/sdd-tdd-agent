import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol, Set, Tuple


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "task_breakdown" / f"{PROMPT_VERSION}.md"
)
REQUIREMENT_HEADING = "# Requirement Analysis"
DESIGN_HEADING = "# Design Proposal"


@dataclass(frozen=True)
class TaskBreakdownRequest:
    """Typed approved context supplied to a task-breakdown generator."""

    prompt_version: str
    prompt: str
    requirement: str
    design: str
    project_metadata: str
    architecture: str
    conventions: str


@dataclass(frozen=True)
class DevelopmentTask:
    """One ordered, independently reviewable implementation task."""

    task_id: str
    title: str
    objective: str
    affected_areas: Tuple[str, ...]
    dependencies: Tuple[str, ...]
    acceptance_criteria: Tuple[str, ...]
    test_targets: Tuple[str, ...]


@dataclass(frozen=True)
class TaskBreakdown:
    """Structured ordered task output returned by a generator."""

    summary: str
    tasks: Tuple[DevelopmentTask, ...]
    global_risks: Tuple[str, ...]
    open_questions: Tuple[str, ...]


class TaskBreakdownGenerator(Protocol):
    """Injectable boundary for a task-breakdown model adapter."""

    def generate(self, request: TaskBreakdownRequest) -> TaskBreakdown:
        """Generate a typed breakdown without mutating project state."""
        ...


@dataclass(frozen=True)
class TaskBreakdownRun:
    """Result of a successful task-breakdown workflow run."""

    session_id: str
    next_state: str
    breakdown: TaskBreakdown


def _validate_session_id(session_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError(f"Invalid session identifier: {session_id}")


def load_task_breakdown_request(
    root: Path,
    session_id: str,
) -> TaskBreakdownRequest:
    """Load versioned approved context for one validated feature Session."""
    _validate_session_id(session_id)
    workspace = root / ".agent"
    session = workspace / "sessions" / session_id
    requirement = (session / "requirement.md").read_text(encoding="utf-8")
    design = (session / "design.md").read_text(encoding="utf-8")
    if not requirement.strip() or not requirement.lstrip().startswith(
        REQUIREMENT_HEADING
    ):
        raise ValueError("Task breakdown requires an analyzed requirement")
    if not design.strip() or not design.lstrip().startswith(DESIGN_HEADING):
        raise ValueError("Task breakdown requires a generated design")
    return TaskBreakdownRequest(
        prompt_version=PROMPT_VERSION,
        prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        requirement=requirement,
        design=design,
        project_metadata=(workspace / "project.yml").read_text(encoding="utf-8"),
        architecture=(workspace / "architecture.md").read_text(encoding="utf-8"),
        conventions=(workspace / "conventions.md").read_text(encoding="utf-8"),
    )


def _render_items(items: Tuple[str, ...]) -> str:
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def _render_task(task: DevelopmentTask) -> str:
    sections = (
        f"## Task {task.task_id}: {task.title}",
        f"### Objective\n\n{task.objective}",
        f"### Affected areas\n\n{_render_items(task.affected_areas)}",
        f"### Dependencies\n\n{_render_items(task.dependencies)}",
        f"### Acceptance criteria\n\n{_render_items(task.acceptance_criteria)}",
        f"### Test targets\n\n{_render_items(task.test_targets)}",
    )
    return "\n\n".join(sections)


def render_task_breakdown(
    request: TaskBreakdownRequest,
    breakdown: TaskBreakdown,
) -> str:
    """Render a structured ordered task breakdown as deterministic Markdown."""
    task_sections = tuple(_render_task(task) for task in breakdown.tasks)
    sections = (
        "# Task Breakdown",
        f"Prompt version: `{request.prompt_version}`",
        f"## Summary\n\n{breakdown.summary}",
        *task_sections,
        f"## Global risks\n\n{_render_items(breakdown.global_risks)}",
        f"## Open questions\n\n{_render_items(breakdown.open_questions)}",
    )
    return "\n\n".join(sections) + "\n"


def _validate_items(name: str, items: Tuple[str, ...], required: bool) -> None:
    if not isinstance(items, tuple):
        raise ValueError(f"Task {name} must be a tuple")
    if required and not items:
        raise ValueError(f"Task {name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"Task {name} must contain non-empty strings")


def _validate_task(task: DevelopmentTask, preceding_ids: Set[str]) -> None:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", task.task_id) is None:
        raise ValueError("Task identifier is invalid")
    if task.task_id in preceding_ids:
        raise ValueError(f"Duplicate task identifier: {task.task_id}")
    if not isinstance(task.title, str) or not task.title.strip():
        raise ValueError("Task title must not be empty")
    if not isinstance(task.objective, str) or not task.objective.strip():
        raise ValueError("Task objective must not be empty")
    _validate_items("affected areas", task.affected_areas, required=False)
    _validate_items("dependencies", task.dependencies, required=False)
    if any(dependency not in preceding_ids for dependency in task.dependencies):
        raise ValueError("Task dependency must reference a preceding task")
    _validate_items("acceptance criteria", task.acceptance_criteria, required=True)
    _validate_items("test targets", task.test_targets, required=True)


def _validate_breakdown(breakdown: TaskBreakdown) -> None:
    if not isinstance(breakdown.summary, str) or not breakdown.summary.strip():
        raise ValueError("Task breakdown summary must not be empty")
    if not isinstance(breakdown.tasks, tuple) or not breakdown.tasks:
        raise ValueError("Task breakdown tasks must not be empty")
    preceding_ids: Set[str] = set()
    for task in breakdown.tasks:
        if not isinstance(task, DevelopmentTask):
            raise ValueError("Task breakdown must contain DevelopmentTask values")
        _validate_task(task, preceding_ids)
        preceding_ids.add(task.task_id)
    _validate_items("global risks", breakdown.global_risks, required=False)
    _validate_items("open questions", breakdown.open_questions, required=False)


def _is_approved(state: Dict[str, object], key: str) -> bool:
    review = state.get(key)
    return isinstance(review, dict) and review.get("decision") == "approved"


def _load_task_state(state_path: Path, session_id: str) -> Dict[str, object]:
    state_value = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state_value, dict):
        raise ValueError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise ValueError("Session state identifier does not match Session")
    if state.get("state") != "TASK_BREAKDOWN":
        raise ValueError("Task breakdown requires TASK_BREAKDOWN state")
    if not _is_approved(state, "requirement_review"):
        raise ValueError("Task breakdown requires approved requirements")
    if not _is_approved(state, "design_review"):
        raise ValueError("Task breakdown requires an approved design")
    return state


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tasks.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def run_task_breakdown(
    root: Path,
    session_id: str,
    generator: TaskBreakdownGenerator,
) -> TaskBreakdownRun:
    """Generate ordered tasks and stop the Session for mandatory review."""
    _validate_session_id(session_id)
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    state = _load_task_state(state_path, session_id)
    request = load_task_breakdown_request(root, session_id)
    breakdown = generator.generate(request)
    if not isinstance(breakdown, TaskBreakdown):
        raise ValueError("Generator must return TaskBreakdown")
    _validate_breakdown(breakdown)

    next_state = "TASK_REVIEW"
    state["state"] = next_state
    rendered = render_task_breakdown(request, breakdown)
    serialized_state = f"{json.dumps(state, indent=2)}\n"
    _atomic_write(session / "tasks.md", rendered)
    _atomic_write(state_path, serialized_state)
    return TaskBreakdownRun(
        session_id=session_id,
        next_state=next_state,
        breakdown=breakdown,
    )
