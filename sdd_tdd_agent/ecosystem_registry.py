from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class EcosystemCapability:
    """One implemented target-language ecosystem capability."""

    language: str
    status: str
    tools: Tuple[str, ...]
    test_frameworks: Tuple[str, ...]


ECOSYSTEMS = (
    EcosystemCapability(
        language="java",
        status="supported",
        tools=("maven", "gradle"),
        test_frameworks=("junit5",),
    ),
    EcosystemCapability(
        language="typescript",
        status="supported",
        tools=("npm", "pnpm", "yarn"),
        test_frameworks=("jest", "vitest", "angular"),
    ),
)


def list_ecosystems() -> Tuple[EcosystemCapability, ...]:
    """Return the documented implemented ecosystem matrix."""
    return ECOSYSTEMS


def render_ecosystems(ecosystems: Tuple[EcosystemCapability, ...]) -> str:
    """Render deterministic ecosystem discovery without executing tools."""
    lines = []
    for ecosystem in ecosystems:
        lines.extend(
            (
                f"{ecosystem.language}: {ecosystem.status}",
                f"  tools: {', '.join(ecosystem.tools)}",
                f"  test frameworks: {', '.join(ecosystem.test_frameworks)}",
            )
        )
    return "\n".join(lines) + "\n"
