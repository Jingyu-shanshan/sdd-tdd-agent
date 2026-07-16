import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


PACKAGE_MANAGERS = {"npm", "pnpm", "yarn"}
LOCKFILES = {
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
}
DEPENDENCY_FIELDS = ("dependencies", "devDependencies")


class NodeProjectError(ValueError):
    """Safe public error raised for invalid Node project metadata."""


@dataclass(frozen=True)
class NodeProjectMetadata:
    """Strict root Node project metadata used for test command planning."""

    package_manager: str
    test_framework: str
    test_script: str
    is_angular: bool


def _strict_object(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise NodeProjectError(f"package.json contains duplicate key: {key}")
        result[key] = value
    return result


def _load_package(path: Path) -> Dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except json.JSONDecodeError as error:
        raise NodeProjectError("package.json contains invalid JSON") from error
    except OSError as error:
        raise NodeProjectError("package.json could not be read") from error
    if not isinstance(value, dict):
        raise NodeProjectError("package.json must contain a JSON object")
    return value


def _load_test_script(package: Dict[str, object]) -> str:
    scripts = package.get("scripts")
    if not isinstance(scripts, dict) or any(
        not isinstance(key, str) for key in scripts
    ):
        raise NodeProjectError("package.json scripts must be a string map")
    test_script = scripts.get("test")
    if not isinstance(test_script, str) or not test_script.strip():
        raise NodeProjectError("package.json test script must not be empty")
    if any(not isinstance(value, str) for value in scripts.values()):
        raise NodeProjectError("package.json scripts must be a string map")
    if "\0" in test_script:
        raise NodeProjectError("package.json test script contains null bytes")
    return test_script


def _dependency_names(package: Dict[str, object]) -> Set[str]:
    names: Set[str] = set()
    for field in DEPENDENCY_FIELDS:
        value = package.get(field)
        if value is None:
            continue
        if not isinstance(value, dict) or any(
            not isinstance(key, str) or not isinstance(version, str)
            for key, version in value.items()
        ):
            raise NodeProjectError("package.json dependencies must be string maps")
        names.update(value)
    return names


def _field_package_manager(package: Dict[str, object]) -> str:
    value = package.get("packageManager")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise NodeProjectError("packageManager must be a versioned string")
    match = re.fullmatch(r"(npm|pnpm|yarn)@[^\s@]+", value)
    if match is None:
        raise NodeProjectError(
            "packageManager must name npm, pnpm, or yarn with version"
        )
    return match.group(1)


def _detect_package_manager(root: Path, package: Dict[str, object]) -> str:
    configured = _field_package_manager(package)
    lock_managers = {
        manager for marker, manager in LOCKFILES.items() if (root / marker).is_file()
    }
    if len(lock_managers) > 1:
        raise NodeProjectError("Node project contains multiple lockfiles")
    locked = next(iter(lock_managers), "")
    if configured and locked and configured != locked:
        raise NodeProjectError("packageManager conflicts with project lockfile")
    selected = configured or locked
    if not selected:
        raise NodeProjectError(
            "Node package manager is unknown; add packageManager or one lockfile"
        )
    return selected


def _contains_command(script: str, command: str) -> bool:
    return (
        re.search(
            rf"(?:^|[^A-Za-z0-9_-]){re.escape(command)}(?:$|[^A-Za-z0-9_-])",
            script,
        )
        is not None
    )


def _detect_test_framework(
    root: Path,
    script: str,
    dependencies: Set[str],
) -> str:
    has_ng_test = re.search(r"(?:^|[;&|]\s*|\s)ng\s+test(?:\s|$)", script) is not None
    has_angular_workspace = (root / "angular.json").is_file()
    has_angular_dependency = "@angular/core" in dependencies
    angular = has_ng_test and has_angular_workspace and has_angular_dependency
    if has_ng_test and not angular:
        raise NodeProjectError(
            "Angular evidence requires angular.json, @angular/core, and ng test"
        )
    candidates: Set[str] = set()
    if angular:
        candidates.add("angular")
    if "jest" in dependencies and _contains_command(script, "jest"):
        candidates.add("jest")
    if "vitest" in dependencies and _contains_command(script, "vitest"):
        candidates.add("vitest")
    if len(candidates) > 1:
        raise NodeProjectError("Node test script selects multiple test frameworks")
    if not candidates:
        raise NodeProjectError("Node test framework could not be verified")
    return next(iter(candidates))


def load_node_project(root: Path) -> NodeProjectMetadata:
    """Load strict package-manager and test-framework metadata without mutation."""
    package = _load_package(root / "package.json")
    script = _load_test_script(package)
    dependencies = _dependency_names(package)
    manager = _detect_package_manager(root, package)
    framework = _detect_test_framework(root, script, dependencies)
    return NodeProjectMetadata(
        package_manager=manager,
        test_framework=framework,
        test_script=script,
        is_angular=framework == "angular",
    )
