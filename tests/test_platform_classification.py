from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sdd_tdd_agent.platform_contract import PlatformDoctor


@dataclass(frozen=True)
class FixedEnvironment:
    system: str
    version: Tuple[int, int, int] = (3, 12, 0)
    release: Optional[str] = None
    temporary_available: bool = True

    def system_name(self) -> str:
        return self.system

    def python_version(self) -> Tuple[int, int, int]:
        return self.version

    def os_release(self) -> Optional[str]:
        return self.release

    def temporary_directory_available(self) -> bool:
        return self.temporary_available


@pytest.mark.parametrize(
    ("environment", "family", "support", "readiness"),
    [
        (FixedEnvironment("darwin"), "macos", "supported", "ready"),
        (
            FixedEnvironment("linux", release="ID=ubuntu\nVERSION_ID=24.04\n"),
            "linux",
            "compatible-untested",
            "review-required",
        ),
        (FixedEnvironment("win32"), "win32", "unsupported", "unsupported"),
        (
            FixedEnvironment("linux", release="ID=linuxmint\n", version=(3, 8, 20)),
            "linux",
            "supported-target",
            "degraded",
        ),
        (
            FixedEnvironment(
                "linux",
                release="ID=linuxmint\n",
                temporary_available=False,
            ),
            "linux",
            "supported-target",
            "degraded",
        ),
    ],
)
def test_should_classify_platform_and_runtime_readiness(
    environment: FixedEnvironment,
    family: str,
    support: str,
    readiness: str,
) -> None:
    diagnostic = PlatformDoctor(environment).diagnose()

    assert diagnostic.os_family == family
    assert diagnostic.platform_support == support
    assert diagnostic.readiness == readiness
