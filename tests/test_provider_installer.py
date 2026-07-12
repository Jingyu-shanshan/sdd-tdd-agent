from pathlib import Path
from typing import List, Optional, Tuple

from sdd_tdd_agent.model_adapter import ProcessResult
from sdd_tdd_agent.provider_tools import ProviderInstaller


class InstalledLocator:
    def locate(self, executable: str) -> Optional[str]:
        return "/home/user/.local/bin/codex"


class RecordingInstallRunner:
    def __init__(self) -> None:
        self.commands: List[Tuple[str, ...]] = []
        self.timeouts: List[float] = []

    def run(
        self,
        command: Tuple[str, ...],
        stdin: str,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        self.timeouts.append(timeout_seconds)
        if command[0] == "curl":
            script_path = Path(command[command.index("--output") + 1])
            script_path.write_text("#!/bin/sh\n", encoding="utf-8")
            return ProcessResult(0, "download-details", "")
        if command[0] == "sh":
            assert Path(command[1]).read_text(encoding="utf-8") == "#!/bin/sh\n"
            return ProcessResult(0, "install-details", "")
        return ProcessResult(0, "codex-cli 2.0.0\n", "")


def test_should_download_install_and_verify_codex_without_shell_pipeline() -> None:
    runner = RecordingInstallRunner()
    installer = ProviderInstaller(
        runner=runner,
        locator=InstalledLocator(),
        timeout_seconds=120,
    )

    result = installer.install("codex")

    download = runner.commands[0]
    script_path = download[download.index("--output") + 1]
    assert download == (
        "curl",
        "-fsSL",
        "--output",
        script_path,
        "https://chatgpt.com/codex/install.sh",
    )
    assert runner.commands[1] == ("sh", script_path)
    assert runner.commands[2] == (
        "/home/user/.local/bin/codex",
        "--version",
    )
    assert runner.timeouts == [120, 120, 120]
    assert result.provider_key == "codex"
    assert result.version == "codex-cli 2.0.0"
    assert not Path(script_path).exists()
