from pathlib import Path
from typing import Callable, Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import (
    CommandAnalyzerConfig,
    ProcessResult,
    RequirementAnalyzerError,
)
from sdd_tdd_agent.provider_streaming import ProviderStreamingRunner
from sdd_tdd_agent.provider_tools import ProviderDoctor, render_provider_diagnostic


PI_ESM_ERROR = (
    "TypeError: unsupported syntax\n"
    "    at ESMLoader.moduleProvider (node:internal/modules/esm/loader:468:14)\n"
)


class PiRuntimeLocator:
    def locate(self, executable: str) -> Optional[str]:
        return {
            "pi": "/usr/local/bin/pi",
            "node": "/usr/local/bin/node",
        }.get(executable)


class PiRuntimeRunner:
    def __init__(self) -> None:
        self.commands: list[Tuple[str, ...]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        if command[-1] == "--version" and command[0].endswith("/node"):
            return ProcessResult(0, "v20.18.0\n", "")
        return ProcessResult(1, "", PI_ESM_ERROR)


class FailingPiStream:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        return ProcessResult(1, "", PI_ESM_ERROR)


def test_should_explain_pi_node_runtime_incompatibility() -> None:
    runner = PiRuntimeRunner()
    doctor = ProviderDoctor(runner, PiRuntimeLocator(), 30)

    diagnostic = doctor.diagnose("pi")

    assert runner.commands == [
        ("/usr/local/bin/pi", "--version"),
        ("/usr/local/bin/node", "--version"),
    ]
    assert diagnostic.cli_status == "unhealthy"
    assert diagnostic.version is None
    assert diagnostic.detail == (
        "Pi requires Node.js >= 22.19.0; detected v20.18.0. "
        "Upgrade Node.js, then reinstall or update Pi."
    )
    assert "Node.js >= 22.19.0" in render_provider_diagnostic(diagnostic)


def test_should_explain_pi_esm_failure_during_conversation(tmp_path: Path) -> None:
    runner = ProviderStreamingRunner(
        CommandAnalyzerConfig(("pi",), 30, "pi-exec"),
        tmp_path,
        FailingPiStream(),
        lambda event: None,
    )

    with pytest.raises(RequirementAnalyzerError, match="Node.js >= 22.19.0"):
        runner.run(("pi", "--mode", "rpc"), "request", 30)
