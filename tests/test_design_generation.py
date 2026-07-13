import json
from pathlib import Path
from typing import Optional

import pytest

from sdd_tdd_agent.design_generation import (
    DesignGenerationRequest,
    DesignProposal,
    load_design_generation_request,
    render_design_proposal,
    run_design_generation,
)


def _proposal() -> DesignProposal:
    return DesignProposal(
        overview="Add export behind an application service.",
        architecture_decisions=("Keep PDF concerns outside CLI dispatch.",),
        components=("Export service coordinates rendering and output.",),
        data_flow=("CLI input -> export service -> PDF output.",),
        interfaces=("PdfExporter.export(source, destination)",),
        error_handling=("Reject unsupported sources before writing.",),
        security_considerations=("Do not include secrets in diagnostics.",),
        testing_strategy=("Unit test the service through an injected writer.",),
        risks_and_tradeoffs=("PDF layout requirements remain uncertain.",),
        open_questions=("Which source artifact is supported?",),
    )


def _create_design_workspace(
    root: Path,
    *,
    state: object = None,
    design: str = "# Design\n\nPending requirement analysis.\n",
) -> Path:
    workspace = root / ".agent"
    session = workspace / "sessions" / "feature-1"
    session.mkdir(parents=True)
    (workspace / "project.yml").write_text("name: reports\n", encoding="utf-8")
    (workspace / "architecture.md").write_text(
        "# Architecture\n\nThin CLI.\n",
        encoding="utf-8",
    )
    (workspace / "conventions.md").write_text(
        "# Conventions\n\nUse typed boundaries.\n",
        encoding="utf-8",
    )
    (session / "requirement.md").write_text(
        "# Requirement Analysis\n\n## Summary\n\nExport reports.\n",
        encoding="utf-8",
    )
    (session / "design.md").write_text(design, encoding="utf-8")
    initial_state = state
    if initial_state is None:
        initial_state = {
            "session_id": "feature-1",
            "kind": "feature",
            "state": "DESIGN",
            "current_task": None,
            "current_cycle": 0,
            "requirement_review": {"decision": "approved"},
        }
    (session / "state.json").write_text(
        json.dumps(initial_state),
        encoding="utf-8",
    )
    return session


class FakeDesignGenerator:
    def __init__(self, proposal: object = None) -> None:
        self.received_request: Optional[DesignGenerationRequest] = None
        self._proposal = _proposal() if proposal is None else proposal

    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
        self.received_request = request
        return self._proposal  # type: ignore[return-value]


class UnexpectedDesignGenerator:
    def generate(self, request: DesignGenerationRequest) -> DesignProposal:
        raise AssertionError("Generator must not run before state validation")


def test_should_load_versioned_design_context(tmp_path: Path) -> None:
    _create_design_workspace(tmp_path)

    request = load_design_generation_request(tmp_path, "feature-1")

    assert request.prompt_version == "v1"
    assert "Design Generation Prompt" in request.prompt
    assert "Export reports" in request.requirement
    assert "name: reports" in request.project_metadata
    assert "Thin CLI" in request.architecture
    assert "typed boundaries" in request.conventions


def test_should_render_structured_design_in_stable_order() -> None:
    request = DesignGenerationRequest(
        prompt_version="v1",
        prompt="Prompt",
        requirement="Approved requirement",
        project_metadata="name: reports",
        architecture="Thin CLI",
        conventions="Typed boundaries",
    )

    rendered = render_design_proposal(request, _proposal())

    headings = (
        "# Design Proposal",
        "## Overview",
        "## Architecture decisions",
        "## Components",
        "## Data flow",
        "## Interfaces",
        "## Error handling",
        "## Security considerations",
        "## Testing strategy",
        "## Risks and trade-offs",
        "## Open questions",
    )
    positions = tuple(rendered.index(heading) for heading in headings)
    assert positions == tuple(sorted(positions))
    assert "Prompt version: `v1`" in rendered
    assert "- Keep PDF concerns outside CLI dispatch." in rendered


def test_should_run_injected_generator_and_enter_design_review(tmp_path: Path) -> None:
    session = _create_design_workspace(tmp_path)
    generator = FakeDesignGenerator()

    run = run_design_generation(tmp_path, "feature-1", generator)

    assert generator.received_request is not None
    assert run.session_id == "feature-1"
    assert run.next_state == "DESIGN_REVIEW"
    assert run.proposal == _proposal()
    assert "# Design Proposal" in (session / "design.md").read_text(
        encoding="utf-8"
    )
    state = json.loads((session / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "DESIGN_REVIEW"
    assert state["requirement_review"] == {"decision": "approved"}


@pytest.mark.parametrize(
    "state",
    [
        {
            "session_id": "feature-1",
            "state": "REQUIREMENT_REVIEW",
            "requirement_review": {"decision": "approved"},
        },
        {
            "session_id": "feature-1",
            "state": "DESIGN",
            "requirement_review": {"decision": "rejected"},
        },
        {
            "session_id": "another-session",
            "state": "DESIGN",
            "requirement_review": {"decision": "approved"},
        },
        ["not", "an", "object"],
    ],
)
def test_should_reject_invalid_state_before_generator_and_mutation(
    tmp_path: Path,
    state: object,
) -> None:
    session = _create_design_workspace(tmp_path, state=state)
    original_design = (session / "design.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_design_generation(tmp_path, "feature-1", UnexpectedDesignGenerator())

    assert (session / "design.md").read_text(encoding="utf-8") == original_design
    assert (session / "state.json").read_text(encoding="utf-8") == original_state


@pytest.mark.parametrize(
    "proposal",
    [
        object(),
        DesignProposal(
            overview="",
            architecture_decisions=("A decision.",),
            components=("A component.",),
            data_flow=("A flow.",),
            interfaces=(),
            error_handling=(),
            security_considerations=(),
            testing_strategy=("A test strategy.",),
            risks_and_tradeoffs=(),
            open_questions=(),
        ),
        DesignProposal(
            overview="Overview.",
            architecture_decisions=("A decision.",),
            components=(" ",),
            data_flow=("A flow.",),
            interfaces=(),
            error_handling=(),
            security_considerations=(),
            testing_strategy=("A test strategy.",),
            risks_and_tradeoffs=(),
            open_questions=(),
        ),
    ],
)
def test_should_reject_invalid_generator_output_before_mutation(
    tmp_path: Path,
    proposal: object,
) -> None:
    session = _create_design_workspace(tmp_path)
    original_design = (session / "design.md").read_text(encoding="utf-8")
    original_state = (session / "state.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        run_design_generation(
            tmp_path,
            "feature-1",
            FakeDesignGenerator(proposal),
        )

    assert (session / "design.md").read_text(encoding="utf-8") == original_design
    assert (session / "state.json").read_text(encoding="utf-8") == original_state
