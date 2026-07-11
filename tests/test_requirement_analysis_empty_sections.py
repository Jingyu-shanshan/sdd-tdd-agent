from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysis,
    RequirementAnalysisRequest,
    render_requirement_analysis,
)


def test_should_render_empty_optional_sections_explicitly() -> None:
    request = RequirementAnalysisRequest(
        prompt_version="v1",
        prompt="Prompt content",
        user_request="Support PDF export",
        project_metadata="name: reports",
        architecture="# Architecture",
        conventions="# Conventions",
    )
    analysis = RequirementAnalysis(
        summary="Export reports as PDFs.",
        user_stories=("As a user, I can export a report as PDF.",),
        functional_requirements=("Provide a PDF export action.",),
        non_functional_requirements=(),
        impact_analysis=(),
        open_questions=(),
    )

    rendered = render_requirement_analysis(request, analysis)

    assert rendered.count("- None identified.") == 3
