from typing import Optional, Tuple

from sdd_tdd_agent.platform_contract import PlatformDoctor, render_platform_diagnostic


class LinuxMintEnvironment:
    def system_name(self) -> str:
        return "linux"

    def python_version(self) -> Tuple[int, int, int]:
        return (3, 12, 4)

    def os_release(self) -> Optional[str]:
        return 'NAME="Linux Mint"\nID=linuxmint\nVERSION_ID="22.1"\n'

    def temporary_directory_available(self) -> bool:
        return True


def test_should_report_linux_mint_as_ready_supported_target() -> None:
    diagnostic = PlatformDoctor(LinuxMintEnvironment()).diagnose()

    assert diagnostic.os_family == "linux"
    assert diagnostic.distribution_id == "linuxmint"
    assert diagnostic.distribution_version == "22.1"
    assert diagnostic.platform_support == "supported-target"
    assert diagnostic.python_status == "supported"
    assert diagnostic.temporary_directory_status == "available"
    assert diagnostic.readiness == "ready"
    assert render_platform_diagnostic(diagnostic) == """\
Operating system: linux
Distribution: linuxmint 22.1
Platform support: supported-target
Python: 3.12.4 (supported)
Temporary directory: available
Readiness: ready
"""
