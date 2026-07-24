from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.clipboard import SystemClipboard
from sdd_tdd_agent.model_adapter import ProcessResult


class Locator:
    def __init__(self, commands: dict[str, Optional[str]]) -> None:
        self.commands = commands

    def locate(self, executable: str) -> Optional[str]:
        return self.commands.get(executable)


class Runner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[tuple[Tuple[str, ...], str]] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, stdin))
        return ProcessResult(self.returncode, "", "")


def test_should_copy_with_macos_native_clipboard() -> None:
    runner = Runner()
    clipboard = SystemClipboard(
        runner,
        Locator({"pbcopy": "/usr/bin/pbcopy"}),
        platform="darwin",
    )

    clipboard.copy("reply")

    assert runner.calls == [(("/usr/bin/pbcopy",), "reply")]


def test_should_explain_when_linux_clipboard_is_unavailable() -> None:
    clipboard = SystemClipboard(Runner(), Locator({}), platform="linux")

    with pytest.raises(ValueError, match="No supported clipboard command"):
        clipboard.copy("reply")
