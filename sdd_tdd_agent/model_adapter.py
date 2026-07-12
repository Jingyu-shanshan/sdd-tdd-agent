import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Protocol, Tuple

from sdd_tdd_agent.requirement_analysis import (
    RequirementAnalysis,
    RequirementAnalysisRequest,
)


ANALYSIS_KEYS = {
    "summary",
    "user_stories",
    "functional_requirements",
    "non_functional_requirements",
    "impact_analysis",
    "open_questions",
}

ANALYSIS_SCHEMA: Dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "user_stories": {"type": "array", "items": {"type": "string"}},
        "functional_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "non_functional_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "impact_analysis": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "user_stories",
        "functional_requirements",
        "non_functional_requirements",
        "impact_analysis",
        "open_questions",
    ],
    "additionalProperties": False,
}

CODEX_FALLBACK_PATHS = (Path("/Applications/ChatGPT.app/Contents/Resources/codex"),)


class RequirementAnalyzerError(RuntimeError):
    """Safe public error raised by a requirement analyzer adapter."""


@dataclass(frozen=True)
class CommandAnalyzerConfig:
    """Validated shell-free analyzer command configuration."""

    command: Tuple[str, ...]
    timeout_seconds: float
    protocol: str = "json-command"

    def __post_init__(self) -> None:
        if not self.command or any(
            not isinstance(argument, str) or not argument.strip()
            for argument in self.command
        ):
            raise ValueError("Analyzer command must contain non-empty arguments")
        if any("\x00" in argument for argument in self.command):
            raise ValueError("Analyzer command arguments must not contain null bytes")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("Analyzer timeout must be a positive finite number")
        if self.protocol not in {"json-command", "codex-exec"}:
            raise ValueError("Analyzer protocol is invalid")


@dataclass(frozen=True)
class ProcessResult:
    """Captured process result without logging or side effects."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Typed and mockable external process tool boundary."""

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        """Execute one already-tokenized command without a shell."""
        ...


class CodexCommandResolver(Protocol):
    """Typed boundary for resolving the configured Codex executable."""

    def resolve(self, executable: str) -> str:
        """Resolve one configured executable without mutating the environment."""
        ...


@dataclass(frozen=True)
class SystemCodexCommandResolver:
    """Resolve Codex from PATH or a verified platform installation path."""

    path_lookup: Callable[[str], Optional[str]] = shutil.which
    fallback_paths: Tuple[Path, ...] = CODEX_FALLBACK_PATHS

    def resolve(self, executable: str) -> str:
        """Preserve PATH commands and fall back only for the standard name."""
        if self.path_lookup(executable) is not None or executable != "codex":
            return executable
        for candidate in self.fallback_paths:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return executable


class SubprocessRunner:
    """Production process runner that never invokes a command shell."""

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        """Execute a tokenized process with captured standard streams."""
        try:
            completed = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RequirementAnalyzerError("Analyzer command timed out") from error
        except OSError as error:
            raise RequirementAnalyzerError(
                "Analyzer command could not be started"
            ) from error
        return ProcessResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _request_payload(request: RequirementAnalysisRequest) -> Dict[str, str]:
    return {
        "prompt_version": request.prompt_version,
        "prompt": request.prompt,
        "user_request": request.user_request,
        "project_metadata": request.project_metadata,
        "architecture": request.architecture,
        "conventions": request.conventions,
    }


def _string_tuple(payload: Dict[str, object], key: str) -> Tuple[str, ...]:
    value = payload[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RequirementAnalyzerError(f"Analyzer field has invalid type: {key}")
    return tuple(value)


def _decode_analysis(stdout: str) -> RequirementAnalysis:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise RequirementAnalyzerError("Analyzer returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise RequirementAnalyzerError("Analyzer response must be a JSON object")
    if set(payload) != ANALYSIS_KEYS:
        raise RequirementAnalyzerError("Analyzer response keys do not match schema")
    summary = payload["summary"]
    if not isinstance(summary, str):
        raise RequirementAnalyzerError("Analyzer field has invalid type: summary")
    return RequirementAnalysis(
        summary=summary,
        user_stories=_string_tuple(payload, "user_stories"),
        functional_requirements=_string_tuple(payload, "functional_requirements"),
        non_functional_requirements=_string_tuple(
            payload,
            "non_functional_requirements",
        ),
        impact_analysis=_string_tuple(payload, "impact_analysis"),
        open_questions=_string_tuple(payload, "open_questions"),
    )


class JsonCommandRequirementAnalyzer:
    """Requirement analyzer using a strict JSON command protocol."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
    ) -> None:
        self._config = config
        self._runner = runner

    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        """Exchange one typed analysis request through the configured runner."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        result = self._runner.run(
            self._config.command,
            stdin,
            self._config.timeout_seconds,
        )
        if result.returncode != 0:
            raise RequirementAnalyzerError(
                f"Analyzer command failed with exit code {result.returncode}"
            )
        return _decode_analysis(result.stdout)


class CodexExecRequirementAnalyzer:
    """Requirement analyzer backed by an ephemeral read-only Codex CLI run."""

    def __init__(
        self,
        config: CommandAnalyzerConfig,
        runner: ProcessRunner,
        workspace: Path,
        command_resolver: Optional[CodexCommandResolver] = None,
    ) -> None:
        if len(config.command) != 1:
            raise ValueError("Codex analyzer command must contain one executable")
        self._config = config
        self._runner = runner
        self._workspace = workspace
        resolver = command_resolver or SystemCodexCommandResolver()
        self._executable = resolver.resolve(config.command[0])

    def analyze(self, request: RequirementAnalysisRequest) -> RequirementAnalysis:
        """Exchange one analysis request through a structured Codex exec run."""
        stdin = json.dumps(_request_payload(request), ensure_ascii=False)
        try:
            with tempfile.TemporaryDirectory(prefix="sdd-tdd-codex-") as directory:
                exchange = Path(directory)
                schema_path = exchange / "requirement-analysis.schema.json"
                output_path = exchange / "requirement-analysis.json"
                schema_path.write_text(
                    json.dumps(ANALYSIS_SCHEMA),
                    encoding="utf-8",
                )
                result = self._runner.run(
                    self._command(schema_path, output_path),
                    stdin,
                    self._config.timeout_seconds,
                )
                if result.returncode != 0:
                    raise RequirementAnalyzerError(
                        f"Codex command failed with exit code {result.returncode}"
                    )
                return _decode_analysis(output_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise RequirementAnalyzerError(
                "Codex analyzer output could not be read"
            ) from error

    def _command(self, schema_path: Path, output_path: Path) -> Tuple[str, ...]:
        return (self._executable,) + (
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "--cd",
            str(self._workspace),
            "-",
        )
