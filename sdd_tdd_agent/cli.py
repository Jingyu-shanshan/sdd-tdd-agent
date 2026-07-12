import sys
from pathlib import Path
from typing import Optional, Sequence, TextIO

from sdd_tdd_agent.analyze_command import analyze_active_requirement
from sdd_tdd_agent.feature_session import create_feature_session
from sdd_tdd_agent.model_adapter import (
    ProcessRunner,
    RequirementAnalyzerError,
    SubprocessRunner,
)
from sdd_tdd_agent.project_init import initialize_project
from sdd_tdd_agent.project_status import load_project_status, render_project_status


def hello(out: TextIO) -> None:
    """Write the platform greeting to the supplied output stream."""
    out.write("Hello, World!\n")


def main(
    argv: Optional[Sequence[str]] = None,
    out: Optional[TextIO] = None,
    root: Optional[Path] = None,
    runner: Optional[ProcessRunner] = None,
    err: Optional[TextIO] = None,
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

    return 2
