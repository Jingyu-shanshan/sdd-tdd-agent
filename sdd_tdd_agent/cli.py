import sys
from pathlib import Path
from typing import Optional, Sequence, TextIO

from sdd_tdd_agent.analyze_command import (
    analyze_active_requirement,
    load_analyzer_config,
)
from sdd_tdd_agent.design_command import generate_active_design
from sdd_tdd_agent.design_review import (
    DesignReviewError,
    approve_active_design,
    load_active_design_review,
    reject_active_design,
)
from sdd_tdd_agent.feature_session import create_feature_session
from sdd_tdd_agent.model_adapter import (
    ProcessRunner,
    RequirementAnalyzerError,
    SubprocessRunner,
    SystemCodexCommandResolver,
)
from sdd_tdd_agent.platform_contract import (
    PlatformDoctor,
    SystemPlatformEnvironment,
    render_platform_diagnostic,
)
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.project_status import load_project_status, render_project_status
from sdd_tdd_agent.requirement_review import (
    RequirementReviewError,
    approve_active_requirement,
    load_active_requirement_review,
    reject_active_requirement,
)
from sdd_tdd_agent.provider_registry import (
    list_providers,
    load_provider_selection,
    render_provider_list,
    render_provider_status,
)
from sdd_tdd_agent.provider_tools import (
    ProviderCommandDependencies,
    ProviderDoctor,
    ProviderInstallError,
    render_provider_diagnostic,
    use_provider,
)


def hello(out: TextIO) -> None:
    """Write the platform greeting to the supplied output stream."""
    out.write("Hello, World!\n")


def main(
    argv: Optional[Sequence[str]] = None,
    out: Optional[TextIO] = None,
    root: Optional[Path] = None,
    runner: Optional[ProcessRunner] = None,
    err: Optional[TextIO] = None,
    provider_dependencies: Optional[ProviderCommandDependencies] = None,
) -> int:
    """Run the command-line interface."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    output = sys.stdout if out is None else out
    error_output = sys.stderr if err is None else err
    project_root = Path.cwd() if root is None else root

    if arguments and arguments[0] == "hello":
        hello(output)
        return 0

    if arguments and arguments[0] == "init":
        initialize_project(project_root)
        output.write("Initialized .agent workspace.\n")
        return 0

    if arguments and arguments[0] == "status":
        status = load_project_status(project_root)
        output.write(render_project_status(status))
        return 0

    if arguments and arguments[0] == "feature":
        description = " ".join(arguments[1:])
        session = create_feature_session(project_root, description)
        output.write(f"Created feature session: {session.session_id}\n")
        return 0

    if arguments and arguments[0] == "analyze":
        process_runner = runner if runner is not None else SubprocessRunner()
        try:
            run = analyze_active_requirement(project_root, process_runner)
        except (ValueError, RequirementAnalyzerError) as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(
            "Requirement analysis ready for review: "
            f"{run.session_id} ({run.next_state})\n"
        )
        return 0

    if arguments == ["design"]:
        process_runner = runner if runner is not None else SubprocessRunner()
        try:
            run = generate_active_design(project_root, process_runner)
        except (ValueError, RequirementAnalyzerError) as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(f"Design ready for review: {run.session_id} ({run.next_state})\n")
        return 0

    if arguments == ["design", "show"]:
        try:
            review = load_active_design_review(project_root)
        except DesignReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(review.design)
        return 0

    if arguments == ["design", "approve"]:
        try:
            decision = approve_active_design(project_root)
        except DesignReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(
            f"Design approved: {decision.session_id} ({decision.next_state})\n"
        )
        return 0

    if arguments and arguments[0:2] == ["design", "reject"]:
        try:
            decision = reject_active_design(
                project_root,
                " ".join(arguments[2:]),
            )
        except DesignReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(
            f"Design rejected: {decision.session_id} ({decision.next_state})\n"
        )
        return 0

    if arguments == ["requirement", "show"]:
        try:
            review = load_active_requirement_review(project_root)
        except RequirementReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(review.requirement)
        return 0

    if arguments == ["requirement", "approve"]:
        try:
            decision = approve_active_requirement(project_root)
        except RequirementReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(
            f"Requirement approved: {decision.session_id} ({decision.next_state})\n"
        )
        return 0

    if arguments and arguments[0:2] == ["requirement", "reject"]:
        try:
            decision = reject_active_requirement(
                project_root,
                " ".join(arguments[2:]),
            )
        except RequirementReviewError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(
            f"Requirement rejected: {decision.session_id} ({decision.next_state})\n"
        )
        return 0

    if arguments == ["provider", "list"]:
        output.write(render_provider_list(list_providers()))
        return 0

    if arguments == ["provider", "status"]:
        try:
            selection = load_provider_selection(project_root)
        except ValueError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(render_provider_status(selection))
        return 0

    if len(arguments) in {2, 3} and arguments[0:2] == ["provider", "doctor"]:
        try:
            config = load_analyzer_config(project_root)
            provider_key = (
                arguments[2]
                if len(arguments) == 3
                else load_provider_selection(project_root).provider_key
            )
            dependencies = provider_dependencies or ProviderCommandDependencies(
                input=sys.stdin,
                runner=runner or SubprocessRunner(),
                locator=SystemCodexCommandResolver(),
            )
            diagnostic = ProviderDoctor(
                runner=dependencies.runner,
                locator=dependencies.locator,
                timeout_seconds=config.timeout_seconds,
            ).diagnose(provider_key)
        except (ValueError, RequirementAnalyzerError) as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(render_provider_diagnostic(diagnostic))
        return 0

    if len(arguments) == 3 and arguments[0:2] == ["provider", "use"]:
        try:
            dependencies = provider_dependencies or ProviderCommandDependencies(
                input=sys.stdin,
                runner=runner or SubprocessRunner(),
                locator=SystemCodexCommandResolver(),
            )
            result = use_provider(
                project_root,
                arguments[2],
                dependencies,
                output,
            )
        except (ValueError, ProviderInstallError, RequirementAnalyzerError) as error:
            error_output.write(f"Error: {error}\n")
            return 2
        if result.cancelled:
            output.write("Provider selection cancelled.\n")
            return 2
        if result.installed_version is not None:
            output.write(
                f"Installed provider CLI: {arguments[2]} ({result.installed_version})\n"
            )
        if result.selection is None:
            error_output.write("Error: Provider selection did not complete\n")
            return 2
        output.write(f"Selected provider: {result.selection.provider_key}\n")
        return 0

    if arguments == ["platform", "doctor"]:
        try:
            diagnostic = PlatformDoctor(SystemPlatformEnvironment()).diagnose()
        except ValueError as error:
            error_output.write(f"Error: {error}\n")
            return 2
        output.write(render_platform_diagnostic(diagnostic))
        return 0

    return 2
