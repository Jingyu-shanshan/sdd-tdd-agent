import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol, Tuple


PROMPT_VERSION = "v1"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "design_generation" / f"{PROMPT_VERSION}.md"
)
REQUIREMENT_HEADING = "# Requirement Analysis"


@dataclass(frozen=True)
class DesignGenerationRequest:
    """Typed approved context supplied to a design generator."""

    prompt_version: str
    prompt: str
    requirement: str
    project_metadata: str
    architecture: str
    conventions: str


@dataclass(frozen=True)
class DesignProposal:
    """Structured software design returned by a design generator."""

    overview: str
    architecture_decisions: Tuple[str, ...]
    components: Tuple[str, ...]
    data_flow: Tuple[str, ...]
    interfaces: Tuple[str, ...]
    error_handling: Tuple[str, ...]
    security_considerations: Tuple[str, ...]
    testing_strategy: Tuple[str, ...]
    risks_and_tradeoffs: Tuple[str, ...]
    open_questions: Tuple[str, ...]


class DesignGenerator(Protocol):
    """Injectable boundary for a software-design model adapter."""

    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
        """Generate a typed proposal without mutating project state."""
        ...


@dataclass(frozen=True)
class DesignGenerationRun:
    """Result of a successful design-generation workflow run."""

    session_id: str
    next_state: str
    proposal: DesignProposal


def _validate_session_id(session_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id) is None:
        raise ValueError(f"Invalid session identifier: {session_id}")


def load_design_generation_request(
    root: Path,
    session_id: str,
) -> DesignGenerationRequest:
    """Load versioned design context for one validated feature Session."""
    _validate_session_id(session_id)
    workspace = root / ".agent"
    session = workspace / "sessions" / session_id
    requirement = (session / "requirement.md").read_text(encoding="utf-8")
    if not requirement.strip():
        raise ValueError("Approved requirement must not be empty")
    if not requirement.lstrip().startswith(REQUIREMENT_HEADING):
        raise ValueError("Design generation requires an analyzed requirement")
    return DesignGenerationRequest(
        prompt_version=PROMPT_VERSION,
        prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        requirement=requirement,
        project_metadata=(workspace / "project.yml").read_text(encoding="utf-8"),
        architecture=(workspace / "architecture.md").read_text(encoding="utf-8"),
        conventions=(workspace / "conventions.md").read_text(encoding="utf-8"),
    )


def _render_items(items: Tuple[str, ...]) -> str:
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def render_design_proposal(
    request: DesignGenerationRequest,
    proposal: DesignProposal,
) -> str:
    """Render a structured design proposal as deterministic Markdown."""
    sections = (
        "# Design Proposal",
        f"Prompt version: `{request.prompt_version}`",
        f"## Overview\n\n{proposal.overview}",
        (
            "## Architecture decisions\n\n"
            f"{_render_items(proposal.architecture_decisions)}"
        ),
        f"## Components\n\n{_render_items(proposal.components)}",
        f"## Data flow\n\n{_render_items(proposal.data_flow)}",
        f"## Interfaces\n\n{_render_items(proposal.interfaces)}",
        f"## Error handling\n\n{_render_items(proposal.error_handling)}",
        (
            "## Security considerations\n\n"
            f"{_render_items(proposal.security_considerations)}"
        ),
        f"## Testing strategy\n\n{_render_items(proposal.testing_strategy)}",
        (f"## Risks and trade-offs\n\n{_render_items(proposal.risks_and_tradeoffs)}"),
        f"## Open questions\n\n{_render_items(proposal.open_questions)}",
    )
    return "\n\n".join(sections) + "\n"


def _validate_items(name: str, items: Tuple[str, ...], required: bool) -> None:
    if required and not items:
        raise ValueError(f"Design {name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"Design {name} must contain non-empty strings")


def _validate_proposal(proposal: DesignProposal) -> None:
    if not isinstance(proposal.overview, str) or not proposal.overview.strip():
        raise ValueError("Design overview must not be empty")
    _validate_items("architecture decisions", proposal.architecture_decisions, True)
    _validate_items("components", proposal.components, True)
    _validate_items("data flow", proposal.data_flow, True)
    _validate_items("interfaces", proposal.interfaces, False)
    _validate_items("error handling", proposal.error_handling, False)
    _validate_items(
        "security considerations",
        proposal.security_considerations,
        False,
    )
    _validate_items("testing strategy", proposal.testing_strategy, True)
    _validate_items("risks and trade-offs", proposal.risks_and_tradeoffs, False)
    _validate_items("open questions", proposal.open_questions, False)


def _load_design_state(state_path: Path, session_id: str) -> Dict[str, object]:
    state_value = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state_value, dict):
        raise ValueError("Session state must be a JSON object")
    state: Dict[str, object] = state_value
    if state.get("session_id") != session_id:
        raise ValueError("Session state identifier does not match Session")
    if state.get("state") != "DESIGN":
        raise ValueError("Design generation requires DESIGN state")
    review = state.get("requirement_review")
    if not isinstance(review, dict) or review.get("decision") != "approved":
        raise ValueError("Design generation requires approved requirements")
    return state


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.design.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def run_design_generation(
    root: Path,
    session_id: str,
    generator: DesignGenerator,
) -> DesignGenerationRun:
    """Generate a design and stop the Session for mandatory human review."""
    _validate_session_id(session_id)
    session = root / ".agent" / "sessions" / session_id
    state_path = session / "state.json"
    state = _load_design_state(state_path, session_id)
    request = load_design_generation_request(root, session_id)
    proposal = generator.generate(request)
    if not isinstance(proposal, DesignProposal):
        raise ValueError("Generator must return DesignProposal")
    _validate_proposal(proposal)

    next_state = "DESIGN_REVIEW"
    state["state"] = next_state
    rendered = render_design_proposal(request, proposal)
    serialized_state = f"{json.dumps(state, indent=2)}\n"
    _atomic_write(session / "design.md", rendered)
    _atomic_write(state_path, serialized_state)
    return DesignGenerationRun(
        session_id=session_id,
        next_state=next_state,
        proposal=proposal,
    )
