import json
from pathlib import Path

import pytest

from sdd_tdd_agent.node_project import NodeProjectError, load_node_project
from sdd_tdd_agent.project_detection import ProjectProfile, detect_project


def _write_package(root: Path, payload: object) -> None:
    (root / "package.json").write_text(json.dumps(payload), encoding="utf-8")


def _package(
    manager: object = "npm@11.0.0",
    script: object = "jest",
    dependencies: object = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "reports",
        "packageManager": manager,
        "scripts": {"test": script},
        "devDependencies": {"jest": "30.0.0"},
    }
    if dependencies is not None:
        payload["devDependencies"] = dependencies
    return payload


@pytest.mark.parametrize(
    ("marker", "manager"),
    [
        ("package-lock.json", "npm"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
    ],
)
def test_should_detect_package_manager_from_one_lockfile(
    tmp_path: Path,
    marker: str,
    manager: str,
) -> None:
    payload = _package(manager=None)
    del payload["packageManager"]
    _write_package(tmp_path, payload)
    (tmp_path / marker).write_text("lock\n")

    metadata = load_node_project(tmp_path)

    assert metadata.package_manager == manager
    assert metadata.test_framework == "jest"
    assert metadata.test_script == "jest"


def test_should_accept_consistent_package_manager_field_and_lock(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        _package(
            manager="pnpm@10.2.0",
            script="vitest",
            dependencies={"vitest": "4.0.0"},
        ),
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lock\n")

    metadata = load_node_project(tmp_path)

    assert metadata.package_manager == "pnpm"


def test_should_detect_angular_from_complete_workspace_evidence(
    tmp_path: Path,
) -> None:
    _write_package(
        tmp_path,
        _package(
            manager="yarn@4.6.0",
            script="ng test",
            dependencies={"@angular/core": "21.0.0"},
        ),
    )
    (tmp_path / "angular.json").write_text('{"projects": {}}')

    metadata = load_node_project(tmp_path)

    assert metadata.package_manager == "yarn"
    assert metadata.test_framework == "angular"
    assert metadata.is_angular is True


@pytest.mark.parametrize(
    ("payload", "markers", "message"),
    [
        (_package(manager=None), (), "packageManager"),
        (_package(manager="bun@1.0.0"), (), "packageManager"),
        (_package(manager="npm"), (), "packageManager"),
        (_package(manager="npm@11.0.0"), ("pnpm-lock.yaml",), "conflicts"),
        (
            _package(manager=None),
            ("package-lock.json", "yarn.lock"),
            "multiple lockfiles",
        ),
        (_package(script=""), (), "test script"),
        (_package(script=42), (), "test script"),
        (_package(script="node test.js"), (), "framework"),
        (
            _package(script="ng test", dependencies={"@angular/core": "21"}),
            (),
            "Angular evidence",
        ),
        (
            _package(
                script="jest && vitest", dependencies={"jest": "30", "vitest": "4"}
            ),
            (),
            "multiple test frameworks",
        ),
    ],
)
def test_should_reject_ambiguous_or_invalid_node_metadata(
    tmp_path: Path,
    payload: dict[str, object],
    markers: tuple[str, ...],
    message: str,
) -> None:
    if payload.get("packageManager") is None:
        payload.pop("packageManager", None)
    _write_package(tmp_path, payload)
    for marker in markers:
        (tmp_path / marker).write_text("lock\n")

    with pytest.raises(NodeProjectError, match=message):
        load_node_project(tmp_path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not-json", "invalid JSON"),
        ('{"name":"one","name":"two"}', "duplicate key"),
        ("[]", "JSON object"),
        ('{"scripts": []}', "scripts"),
        ('{"scripts": {"test": "jest"}, "devDependencies": []}', "dependencies"),
    ],
)
def test_should_reject_invalid_package_json(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    (tmp_path / "package.json").write_text(content)

    with pytest.raises(NodeProjectError, match=message):
        load_node_project(tmp_path)


def test_should_report_typescript_project_profile(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        _package(manager="pnpm@10", script="vitest", dependencies={"vitest": "4"}),
    )

    assert detect_project(tmp_path) == ProjectProfile(
        target_language="typescript",
        build_tool="pnpm",
        test_frameworks=("vitest",),
    )


def test_should_report_angular_project_profile(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        _package(
            manager="npm@11",
            script="ng test",
            dependencies={"@angular/core": "21"},
        ),
    )
    (tmp_path / "angular.json").write_text("{}")

    assert detect_project(tmp_path) == ProjectProfile(
        target_language="typescript",
        build_tool="npm",
        test_frameworks=("angular",),
    )
