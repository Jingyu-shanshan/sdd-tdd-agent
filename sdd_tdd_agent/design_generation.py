import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Optional, Protocol, Set, Tuple

from sdd_tdd_agent.project_detection import detect_project


PROMPT_VERSION = "v1"
TYPESCRIPT_PROMPT_VERSION = "v2-typescript"
PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "design_generation" / f"{PROMPT_VERSION}.md"
)
TYPESCRIPT_PROMPT_PATH = (
    Path(__file__).parent
    / "prompts"
    / "design_generation"
    / f"{TYPESCRIPT_PROMPT_VERSION}.md"
)
REQUIREMENT_HEADING = "# Requirement Analysis"
TYPESCRIPT_CONFIG_FILES = (
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.spec.json",
)
TYPESCRIPT_API_KINDS = {
    "class",
    "component",
    "constant",
    "directive",
    "function",
    "interface",
    "pipe",
    "service",
    "type",
}


@dataclass(frozen=True)
class TypeScriptProjectContext:
    """Verified TypeScript project evidence supplied to design generation."""

    package_manager: str
    test_framework: str
    is_angular: bool
    config_files: Tuple[str, ...]


@dataclass(frozen=True)
class TypeScriptModuleDesign:
    """One proposed TypeScript source module and its exported surface."""

    path: str
    responsibility: str
    exports: Tuple[str, ...]


@dataclass(frozen=True)
class TypeScriptPublicApiDesign:
    """One proposed public TypeScript API owned by a designed module."""

    name: str
    kind: str
    signature: str
    module: str


@dataclass(frozen=True)
class DesignGenerationRequest:
    """Typed approved context supplied to a design generator."""

    prompt_version: str
    prompt: str
    requirement: str
    project_metadata: str
    architecture: str
    conventions: str
    typescript_context: Optional[TypeScriptProjectContext] = None


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
    typescript_modules: Tuple[TypeScriptModuleDesign, ...] = ()
    public_apis: Tuple[TypeScriptPublicApiDesign, ...] = ()


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


def _typescript_context(root: Path) -> Optional[TypeScriptProjectContext]:
    profile = detect_project(root)
    if profile is None or profile.target_language != "typescript":
        return None
    if len(profile.test_frameworks) != 1:
        raise ValueError("TypeScript project must have one verified test framework")
    framework = profile.test_frameworks[0]
    config_files = tuple(
        name for name in TYPESCRIPT_CONFIG_FILES if (root / name).is_file()
    )
    if not config_files:
        return None
    return TypeScriptProjectContext(
        package_manager=profile.build_tool,
        test_framework=framework,
        is_angular=framework == "angular",
        config_files=config_files,
    )


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
    typescript_context = _typescript_context(root)
    prompt_version = (
        TYPESCRIPT_PROMPT_VERSION if typescript_context is not None else PROMPT_VERSION
    )
    prompt_path = (
        TYPESCRIPT_PROMPT_PATH if typescript_context is not None else PROMPT_PATH
    )
    return DesignGenerationRequest(
        prompt_version=prompt_version,
        prompt=prompt_path.read_text(encoding="utf-8"),
        requirement=requirement,
        project_metadata=(workspace / "project.yml").read_text(encoding="utf-8"),
        architecture=(workspace / "architecture.md").read_text(encoding="utf-8"),
        conventions=(workspace / "conventions.md").read_text(encoding="utf-8"),
        typescript_context=typescript_context,
    )


def _render_items(items: Tuple[str, ...]) -> str:
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def _render_typescript_context(context: TypeScriptProjectContext) -> str:
    configs = ", ".join(f"`{name}`" for name in context.config_files) or "None"
    angular = "yes" if context.is_angular else "no"
    return "\n".join(
        (
            f"- Package manager: `{context.package_manager}`",
            f"- Test framework: `{context.test_framework}`",
            f"- Angular: `{angular}`",
            f"- Config files: {configs}",
        )
    )


def _render_typescript_modules(modules: Tuple[TypeScriptModuleDesign, ...]) -> str:
    sections: list[str] = []
    for module in modules:
        exports = ", ".join(f"`{name}`" for name in module.exports) or "None"
        sections.append(
            "\n".join(
                (
                    f"### `{module.path}`",
                    "",
                    f"- Responsibility: {module.responsibility}",
                    f"- Exports: {exports}",
                )
            )
        )
    return "\n\n".join(sections)


def _render_public_apis(apis: Tuple[TypeScriptPublicApiDesign, ...]) -> str:
    if not apis:
        return "- None identified."
    sections: list[str] = []
    for api in apis:
        sections.append(
            "\n".join(
                (
                    f"### `{api.name}`",
                    "",
                    f"- Kind: `{api.kind}`",
                    f"- Signature: `{api.signature}`",
                    f"- Module: `{api.module}`",
                )
            )
        )
    return "\n\n".join(sections)


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
    if request.typescript_context is not None:
        sections += (
            (
                "## TypeScript project context\n\n"
                f"{_render_typescript_context(request.typescript_context)}"
            ),
            (
                "## TypeScript modules\n\n"
                f"{_render_typescript_modules(proposal.typescript_modules)}"
            ),
            f"## Public APIs\n\n{_render_public_apis(proposal.public_apis)}",
        )
    return "\n\n".join(sections) + "\n"


def _validate_items(name: str, items: Tuple[str, ...], required: bool) -> None:
    if required and not items:
        raise ValueError(f"Design {name} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"Design {name} must contain non-empty strings")


def _safe_typescript_path(value: str) -> None:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        normalized != value
        or path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] != "src"
        or ".." in path.parts
        or path.suffix not in {".ts", ".tsx"}
    ):
        raise ValueError("TypeScript module path must be a safe src path")


def _validate_typescript_design(
    request: DesignGenerationRequest,
    proposal: DesignProposal,
) -> None:
    context = request.typescript_context
    if context is None:
        if proposal.typescript_modules or proposal.public_apis:
            raise ValueError("Non-TypeScript design contains TypeScript records")
        return
    if not proposal.typescript_modules:
        raise ValueError("TypeScript modules must not be empty")
    module_paths: Set[str] = set()
    for module in proposal.typescript_modules:
        if not isinstance(module, TypeScriptModuleDesign):
            raise ValueError("TypeScript modules have invalid type")
        _safe_typescript_path(module.path)
        if module.path in module_paths:
            raise ValueError("TypeScript module paths must be unique")
        module_paths.add(module.path)
        if (
            not module.responsibility.strip()
            or not module.exports
            or any(
                not isinstance(name, str) or not name.strip() for name in module.exports
            )
        ):
            raise ValueError("TypeScript module fields must not be blank")
    api_identities: Set[Tuple[str, str]] = set()
    for api in proposal.public_apis:
        if not isinstance(api, TypeScriptPublicApiDesign):
            raise ValueError("TypeScript public APIs have invalid type")
        if api.module not in module_paths:
            raise ValueError("TypeScript public API must reference a proposed module")
        if api.kind not in TYPESCRIPT_API_KINDS:
            raise ValueError("TypeScript public API kind is unsupported")
        if not api.name.strip() or not api.signature.strip():
            raise ValueError("TypeScript public API fields must not be blank")
        identity = (api.module, api.name)
        if identity in api_identities:
            raise ValueError("TypeScript public API identities must be unique")
        api_identities.add(identity)


def _validate_proposal(
    request: DesignGenerationRequest,
    proposal: DesignProposal,
) -> None:
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
    _validate_typescript_design(request, proposal)


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
    _validate_proposal(request, proposal)

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
