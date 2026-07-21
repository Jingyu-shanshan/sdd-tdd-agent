import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol, Tuple

from sdd_tdd_agent.project_memory import load_project_memory


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "requirement_analysis" / f"{PROMPT_VERSION}.md"
)
USER_REQUEST_MARKER = "## User request"


@dataclass(frozen=True)
class RequirementAnalysisRequest:
    """Typed context supplied to a requirement analyzer."""

    prompt_version: str
    prompt: str
    user_request: str
    project_metadata: str
    architecture: str
    conventions: str


@dataclass(frozen=True)
class RequirementAnalysis:
    """Structured output returned by a requirement analyzer."""

    summary: str
    user_stories: Tuple[str, ...]
    functional_requirements: Tuple[str, ...]
    non_functional_requirements: Tuple[str, ...]
    impact_analysis: Tuple[str, ...]
    open_questions: Tuple[str, ...]


class RequirementAnalyzer(Protocol):
    """Injectable boundary for any requirement-analysis model adapter."""

    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        """Analyze a typed request without mutating project state."""
        ...


@dataclass(frozen=True)
class RequirementAnalysisRun:
    """Result of a successful requirement-analysis workflow run."""

    session_id: str
    next_state: str
    analysis: RequirementAnalysis


def _validate_session_id(session_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError(f"Invalid session identifier: {session_id}")


def _extract_user_request(requirement: str) -> str:
    marker, separator, content = requirement.partition(USER_REQUEST_MARKER)
    if not separator or marker.strip() != "# Requirement":
        raise ValueError(
            "Requirement file does not contain the feature request template"
        )
    user_request = content.strip()
    if not user_request:
        raise ValueError("Feature request must not be empty")
    return user_request


def load_analysis_request(root: Path, session_id: str) -> RequirementAnalysisRequest:
    """Load a typed analysis request for one validated feature session."""
    _validate_session_id(session_id)
    workspace = root / ".agent"
    session = workspace / "sessions" / session_id
    requirement = (session / "requirement.md").read_text(encoding="utf-8")
    memory = load_project_memory(root)
    return RequirementAnalysisRequest(
        prompt_version=PROMPT_VERSION,
        prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        user_request=_extract_user_request(requirement),
        project_metadata=memory.project_metadata,
        architecture=memory.architecture,
        conventions=memory.conventions,
    )


def _render_items(items: Tuple[str, ...]) -> str:
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def render_requirement_analysis(
    request: RequirementAnalysisRequest,
    analysis: RequirementAnalysis,
) -> str:
    """Render structured analysis as deterministic reviewable Markdown."""
    sections = (
        "# Requirement Analysis",
        f"Prompt version: `{request.prompt_version}`",
        f"## Original request\n\n{request.user_request}",
        f"## Summary\n\n{analysis.summary}",
        f"## User stories\n\n{_render_items(analysis.user_stories)}",
        (
            "## Functional requirements\n\n"
            f"{_render_items(analysis.functional_requirements)}"
        ),
        (
            "## Non-functional requirements\n\n"
            f"{_render_items(analysis.non_functional_requirements)}"
        ),
        f"## Impact analysis\n\n{_render_items(analysis.impact_analysis)}",
        f"## Open questions\n\n{_render_items(analysis.open_questions)}",
    )
    return "\n\n".join(sections) + "\n"


def _validate_items(name: str, items: Tuple[str, ...], required: bool) -> None:
    if required and not items:
        raise ValueError(f"Analysis {name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"Analysis {name} must contain non-empty strings")


def _validate_analysis(analysis: RequirementAnalysis) -> None:
    if not isinstance(analysis.summary, str) or not analysis.summary.strip():
        raise ValueError("Analysis summary must not be empty")
    _validate_items("user stories", analysis.user_stories, required=True)
    _validate_items(
        "functional requirements",
        analysis.functional_requirements,
        required=True,
    )
    _validate_items(
        "non-functional requirements",
        analysis.non_functional_requirements,
        required=False,
    )
    _validate_items("impact analysis", analysis.impact_analysis, required=False)
    _validate_items("open questions", analysis.open_questions, required=False)


def _load_analysis_state(state_path: Path) -> Dict[str, object]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("Session state must be a JSON object")
    if state.get("state") != "ANALYSIS":
        raise ValueError("Requirement analysis requires ANALYSIS state")
    return state


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.analysis.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def run_requirement_analysis(
    root: Path,
    session_id: str,
    analyzer: RequirementAnalyzer,
) -> RequirementAnalysisRun:
    """Run injected analysis and stop the Session for mandatory human review."""
    _validate_session_id(session_id)
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    state = _load_analysis_state(state_path)
    request = load_analysis_request(root, session_id)
    analysis = analyzer.analyze(request)
    if not isinstance(analysis, RequirementAnalysis):
        raise ValueError("Analyzer must return RequirementAnalysis")
    _validate_analysis(analysis)

    next_state = "REQUIREMENT_REVIEW"
    state["state"] = next_state
    rendered = render_requirement_analysis(request, analysis)
    serialized_state = f"{json.dumps(state, indent=2)}\n"
    _atomic_write(session / "requirement.md", rendered)
    _atomic_write(state_path, serialized_state)
    return RequirementAnalysisRun(
        session_id=session_id,
        next_state=next_state,
        analysis=analysis,
    )
