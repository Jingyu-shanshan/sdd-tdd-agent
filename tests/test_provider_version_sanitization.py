from typing import Optional, Tuple

from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderDoctor, render_provider_diagnostic


class InstalledLocator:
    def locate(self, executable: str) -> Optional[str]:
        return "/bin/codex"


class ControlSequenceRunner:
    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        return ProcessResult(0, "\x1b[31mcodex-cli SECRET\x1b[0m\n", "")


def test_should_not_render_control_sequences_from_version_output() -> None:
    doctor = ProviderDoctor(
        runner=ControlSequenceRunner(),
        locator=InstalledLocator(),
        timeout_seconds=30,
    )

    diagnostic = doctor.diagnose("codex")
    rendered = render_provider_diagnostic(diagnostic)

    assert diagnostic.cli_status == "unhealthy"
    assert diagnostic.version is None
    assert "SECRET" not in rendered
    assert "\x1b" not in rendered
