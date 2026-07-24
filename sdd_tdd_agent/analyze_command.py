import json
from pathlib import Path
from typing import List, Optional

from sdd_tdd_agent.model_adapter import (
    CodexExecRequirementAnalyzer,
    CommandAnalyzerConfig,
    JsonCommandRequirementAnalyzer,
    ProcessRunner,
    structured_cli_runner,
)
from sdd_tdd_agent.project_status import load_project_status
from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysisRun,
    run_requirement_analysis,
)


COMMAND_KEY = "requirement_analyzer_command"
TIMEOUT_KEY = "requirement_analyzer_timeout_seconds"
PROTOCOL_KEY = "requirement_analyzer_protocol"
SUPPORTED_PROTOCOLS = {
    "json-command",
    "codex-exec",
    "claude-exec",
    "cursor-exec",
    "pi-exec",
}


class AnalyzerConfigurationError(ValueError):
    """Safe error for missing or invalid analyzer configuration."""


class ActiveSessionError(ValueError):
    """Safe error raised when no analyzable active Session is selected."""


def _decode_command_item(value: str) -> str:
    try:
        item = json.loads(value)
    except json.JSONDecodeError as error:
        raise AnalyzerConfigurationError(
            "Analyzer command items must be JSON strings"
        ) from error
    if not isinstance(item, str) or not item:
        raise AnalyzerConfigurationError(
            "Analyzer command items must be non-empty JSON strings"
        )
    return item


def load_analyzer_config(root: Path) -> CommandAnalyzerConfig:
    """Load strict analyzer command configuration from the agent workspace."""
    path = root / ".agent" / "config.yml"
    command: List[str] = []
    timeout: Optional[float] = None
    has_command = False
    has_timeout = False
    has_protocol = False
    in_command = False
    protocol = "json-command"

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise AnalyzerConfigurationError(
            "Project is not initialized; run 'wssagent init' in the project root"
        ) from error

    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if not line[0].isspace():
            in_command = False
            key, separator, scalar = value.partition(":")
            if key == COMMAND_KEY:
                if has_command or not separator or scalar.strip():
                    raise AnalyzerConfigurationError("Invalid analyzer command config")
                has_command = True
                in_command = True
            elif key == TIMEOUT_KEY:
                if has_timeout or not separator or not scalar.strip():
                    raise AnalyzerConfigurationError("Invalid analyzer timeout config")
                has_timeout = True
                try:
                    timeout = float(scalar.strip())
                except ValueError as error:
                    raise AnalyzerConfigurationError(
                        "Invalid analyzer timeout config"
                    ) from error
            elif key == PROTOCOL_KEY:
                selected_protocol = scalar.strip()
                if (
                    has_protocol
                    or not separator
                    or selected_protocol not in SUPPORTED_PROTOCOLS
                ):
                    raise AnalyzerConfigurationError("Invalid analyzer protocol config")
                has_protocol = True
                protocol = selected_protocol
            continue
        if in_command and value.startswith("- "):
            command.append(_decode_command_item(value[2:].strip()))
        elif in_command:
            raise AnalyzerConfigurationError("Invalid analyzer command config")

    if not has_command or not has_timeout or timeout is None:
        raise AnalyzerConfigurationError(
            "Analyzer configuration is incomplete; add "
            "requirement_analyzer_command and requirement_analyzer_timeout_seconds "
            "to .agent/config.yml"
        )
    if protocol == "codex-exec" and len(command) != 1:
        raise AnalyzerConfigurationError(
            "Codex analyzer command must contain one executable"
        )
    if protocol in {"claude-exec", "cursor-exec", "pi-exec"} and len(command) != 1:
        raise AnalyzerConfigurationError(
            "Structured CLI analyzer command must contain one executable"
        )
    try:
        return CommandAnalyzerConfig(tuple(command), timeout, protocol)
    except ValueError as error:
        raise AnalyzerConfigurationError("Analyzer configuration is invalid") from error


def analyze_active_requirement(
    root: Path,
    runner: ProcessRunner,
) -> RequirementAnalysisRun:
    """Run configured requirement analysis for the active project Session."""
    status = load_project_status(root)
    if status.current_session is None:
        raise ActiveSessionError("Project has no active Session")
    config = load_analyzer_config(root)
    if config.protocol == "codex-exec":
        analyzer = CodexExecRequirementAnalyzer(
            config=config,
            runner=runner,
            workspace=root,
        )
    else:
        analyzer = JsonCommandRequirementAnalyzer(
            config=config,
            runner=structured_cli_runner(config, runner),
        )
    return run_requirement_analysis(root, status.current_session, analyzer)
