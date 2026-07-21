from pathlib import Path
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderInstallError, ProviderInstaller


class StageRunner:
    def __init__(self, failure_stage: str) -> None:
        self.failure_stage = failure_stage
        self.call_count = 0

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.call_count += 1
        if command[0] == "curl":
            if self.failure_stage == "download":
                return ProcessResult(17, "SECRET-DOWNLOAD", "SECRET")
            if self.failure_stage != "missing-script":
                path = Path(command[command.index("--output") + 1])
                path.write_text("#!/bin/sh\n", encoding="utf-8")
            return ProcessResult(0, "SECRET-DOWNLOAD", "")
        if command[0] == "sh":
            returncode = 19 if self.failure_stage == "execute" else 0
            return ProcessResult(returncode, "SECRET-INSTALL", "SECRET")
        if self.failure_stage == "version":
            return ProcessResult(23, "SECRET-VERSION", "SECRET")
        if self.failure_stage == "invalid-version":
            return ProcessResult(0, "line-one\nline-two\n", "")
        return ProcessResult(0, "codex-cli 2.0.0\n", "")


class FixedLocator:
    def __init__(self, executable: Optional[str]) -> None:
        self.executable = executable

    def locate(self, executable: str) -> Optional[str]:
        return self.executable


@pytest.mark.parametrize(
    ("stage", "message", "executable"),
    [
        ("download", "Provider installer download failed", "/bin/codex"),
        ("missing-script", "Provider installer download is missing", "/bin/codex"),
        ("execute", "Provider installer execution failed", "/bin/codex"),
        ("success", "Installed provider CLI could not be located", None),
        ("version", "Installed provider CLI verification failed", "/bin/codex"),
        (
            "invalid-version",
            "Installed provider CLI verification failed",
            "/bin/codex",
        ),
    ],
)
def test_should_fail_safely_without_process_content(
    stage: str,
    message: str,
    executable: Optional[str],
) -> None:
    runner = StageRunner(stage)
    installer = ProviderInstaller(
        runner=runner,
        locator=FixedLocator(executable),
        timeout_seconds=30,
    )

    with pytest.raises(ProviderInstallError) as captured:
        installer.install("codex")

    assert str(captured.value) == message
    assert "SECRET" not in str(captured.value)


@pytest.mark.parametrize("provider_key", ["copilot", "custom-json"])
def test_should_reject_provider_without_installable_adapter(
    provider_key: str,
) -> None:
    runner = StageRunner("success")
    installer = ProviderInstaller(
        runner=runner,
        locator=FixedLocator("/bin/provider"),
        timeout_seconds=30,
    )

    with pytest.raises(ProviderInstallError, match="adapter is not installable"):
        installer.install(provider_key)

    assert runner.call_count == 0
