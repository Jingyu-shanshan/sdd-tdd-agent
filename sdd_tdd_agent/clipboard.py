import sys
from typing import Optional, Protocol, Tuple

from sdd_tdd_agent.model_adapter import (
    ProcessRunner,
    RequirementAnalyzerError,
    SubprocessRunner,
)


class ExecutableLocator(Protocol):
    """Locate a platform clipboard executable."""

    def locate(self, executable: str) -> Optional[str]:
        """Return an executable path when available."""
        ...


class SystemExecutableLocator:
    """Locate executable names through the current PATH."""

    def locate(self, executable: str) -> Optional[str]:
        """Return the command path without executing it."""
        import shutil

        return shutil.which(executable)


class Clipboard(Protocol):
    """Injectable clipboard boundary."""

    def copy(self, value: str) -> None:
        """Copy one public Agent reply."""
        ...


class SystemClipboard:
    """Use native macOS or common Linux clipboard commands."""

    def __init__(
        self,
        runner: Optional[ProcessRunner] = None,
        locator: Optional[ExecutableLocator] = None,
        platform: str = sys.platform,
    ) -> None:
        self._runner = runner or SubprocessRunner()
        self._locator = locator or SystemExecutableLocator()
        self._platform = platform

    def copy(self, value: str) -> None:
        """Copy through one located shell-free platform command."""
        command = self._command()
        try:
            result = self._runner.run(command, value, 5.0)
        except RequirementAnalyzerError as error:
            raise ValueError("Clipboard command could not be started") from error
        if result.returncode != 0:
            raise ValueError("Clipboard command failed")

    def _command(self) -> Tuple[str, ...]:
        candidates = (
            (("pbcopy",),)
            if self._platform == "darwin"
            else (
                ("wl-copy",),
                ("xclip", "-selection", "clipboard"),
                ("xsel", "--clipboard", "--input"),
            )
        )
        for candidate in candidates:
            executable = self._locator.locate(candidate[0])
            if executable is not None:
                return (executable, *candidate[1:])
        raise ValueError("No supported clipboard command is available")
