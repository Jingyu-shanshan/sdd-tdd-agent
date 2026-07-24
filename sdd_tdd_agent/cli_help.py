from difflib import get_close_matches
from typing import Dict, Optional, Tuple


CommandUsages = Tuple[Tuple[str, str], ...]
CommandHelp = Tuple[str, CommandUsages]

COMMAND_HELP: Dict[str, CommandHelp] = {
    "hello": ("Verify that the CLI starts.", (("wssagent hello", "Print greeting."),)),
    "update": (
        "Update wssagent from its GitHub repository.",
        (("wssagent update", "Install the latest version in place."),),
    ),
    "init": ("Initialize the .agent workspace.", (("wssagent init", "Initialize."),)),
    "status": (
        "Show project and Session status.",
        (("wssagent status", "Show status."),),
    ),
    "memory": (
        "Inspect project memory metadata.",
        (("wssagent memory", "Show memory."),),
    ),
    "feature": (
        "Start a feature SDD Session.",
        (("wssagent feature <description...>", "Create and activate Session."),),
    ),
    "bug": (
        "Start a bug-fix SDD Session.",
        (("wssagent bug <description...>", "Create and activate Session."),),
    ),
    "analyze": (
        "Analyze the active requirement.",
        (("wssagent analyze", "Run analysis."),),
    ),
    "requirement": (
        "Inspect or decide the requirement review.",
        (
            ("wssagent requirement show", "Show requirement."),
            ("wssagent requirement approve", "Approve requirement."),
            ("wssagent requirement reject <reason...>", "Reject requirement."),
        ),
    ),
    "design": (
        "Generate, inspect, or decide the design.",
        (
            ("wssagent design", "Generate design."),
            ("wssagent design show", "Show design."),
            ("wssagent design approve", "Approve design."),
            ("wssagent design reject <reason...>", "Reject design."),
        ),
    ),
    "tasks": (
        "Generate, inspect, or decide tasks.",
        (
            ("wssagent tasks", "Generate tasks."),
            ("wssagent tasks show", "Show tasks."),
            ("wssagent tasks approve", "Approve tasks."),
            ("wssagent tasks reject <reason...>", "Reject tasks."),
        ),
    ),
    "tests": (
        "Generate the active test plan.",
        (("wssagent tests", "Generate test plan."),),
    ),
    "continue": (
        "Advance the incremental TDD workflow.",
        (("wssagent continue", "Run the next TDD action."),),
    ),
    "review": (
        "Run semantic or deterministic review.",
        (
            ("wssagent review semantic", "Run semantic review."),
            ("wssagent review", "Run deterministic review."),
        ),
    ),
    "refactor": (
        "Run final refactor verification.",
        (
            ("wssagent refactor automated", "Apply verified model refactor."),
            ("wssagent refactor", "Verify without source changes."),
        ),
    ),
    "metrics": (
        "Inspect workflow or quality metrics.",
        (
            ("wssagent metrics", "Show workflow metrics."),
            ("wssagent metrics quality", "Show quality metrics."),
        ),
    ),
    "failures": ("Inspect failure memory.", (("wssagent failures", "Show failures."),)),
    "approval": (
        "Inspect or decide risky changes.",
        (
            ("wssagent approval status", "Show approval."),
            ("wssagent approval approve", "Approve change."),
            ("wssagent approval reject <reason...>", "Reject change."),
        ),
    ),
    "git": (
        "Prepare or create scoped GREEN commits.",
        (
            ("wssagent git prepare", "Prepare commit approval."),
            ("wssagent git commit", "Commit approved artifacts."),
        ),
    ),
    "rollback": (
        "Roll back the current committed GREEN cycle.",
        (("wssagent rollback", "Restore the cycle for retry."),),
    ),
    "ecosystem": (
        "List supported project ecosystems.",
        (("wssagent ecosystem list", "List ecosystems."),),
    ),
    "provider": (
        "List, inspect, diagnose, or select Agent Providers.",
        (
            ("wssagent provider list", "List supported Providers."),
            ("wssagent provider status [--for test|code]", "Show selection."),
            ("wssagent provider doctor [provider]", "Check Provider CLI."),
            (
                "wssagent provider use <provider> [--for test|code]",
                "Select Provider.",
            ),
        ),
    ),
    "platform": (
        "Inspect host platform readiness.",
        (("wssagent platform doctor", "Run platform checks."),),
    ),
    "integration": (
        "Inspect the external integration contract.",
        (("wssagent integration manifest", "Print JSON manifest."),),
    ),
}


def render_help(topic: Optional[str] = None) -> str:
    """Render global or command-specific CLI usage without side effects."""
    if topic is None:
        lines = ["Usage: wssagent <command> [options]", "", "Commands:"]
        for command, (summary, _) in COMMAND_HELP.items():
            lines.append(f"  {command:<12} {summary}")
        lines.extend(
            (
                "",
                "Interactive:",
                "  wssagent",
                "  wssagent -c",
                "  wssagent --resume [id|name]",
                '  wssagent "request"',
                "",
                "Common queries:",
                "  wssagent provider list",
                "  wssagent provider status",
                "  wssagent ecosystem list",
                "",
                "Run 'wssagent <command> --help' for command usage.",
            )
        )
        return "\n".join(lines) + "\n"
    try:
        summary, usages = COMMAND_HELP[topic]
    except KeyError as error:
        raise ValueError(f"Unknown help topic: {topic}") from error
    usage = (
        f"Usage: {usages[0][0]}"
        if len(usages) == 1
        else f"Usage: wssagent {topic} <command>"
    )
    lines = [usage, "", summary, "", "Commands:"]
    lines.extend(f"  {syntax:<68} {description}" for syntax, description in usages)
    return "\n".join(lines) + "\n"


def render_command_error(arguments: Tuple[str, ...]) -> str:
    """Render one safe actionable error for unmatched CLI arguments."""
    command = arguments[0]
    if command in COMMAND_HELP:
        return (
            f"Error: Invalid arguments for command '{command}'.\n"
            f"Run 'wssagent {command} --help' for usage.\n"
        )
    suggestion = get_close_matches(command, COMMAND_HELP, n=1, cutoff=0.6)
    hint = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    return (
        f"Error: Unknown command '{command}'.{hint}\n"
        "Run 'wssagent --help' to list available commands.\n"
    )
