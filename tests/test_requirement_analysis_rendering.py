from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysis,
    RequirementAnalysisRequest,
    render_requirement_analysis,
)


def test_should_render_structured_requirement_analysis() -> None:
    request = RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="Prompt content",
        user_request="Support PDF export",
        project_metadata="name: reports",
        architecture="Hexagonal architecture",
        conventions="Use JUnit 5",
    )
    analysis = RequirementAnalysis(
        summary="Export reports as PDF documents.",
        user_stories=("As a user, I can export a report as PDF.",),
        functional_requirements=("Provide a PDF export action.",),
        non_functional_requirements=("Preserve report data accuracy.",),
        impact_analysis=("The report delivery boundary may be affected.",),
        open_questions=("Which report layouts are in scope?",),
    )

    rendered = render_requirement_analysis(request, analysis)

    assert (
        rendered
        == """\
# Requirement Analysis

Prompt version: `v1`

## Original request

Support PDF export

## Summary

Export reports as PDF documents.

## User stories

- As a user, I can export a report as PDF.

## Functional requirements

- Provide a PDF export action.

## Non-functional requirements

- Preserve report data accuracy.

## Impact analysis

- The report delivery boundary may be affected.

## Open questions

- Which report layouts are in scope?
"""
    )
