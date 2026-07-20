import json
from pathlib import Path

import pytest

from sdd_tdd_agent.angular_workspace import (
    AngularProject,
    AngularWorkspace,
    AngularWorkspaceError,
    load_angular_workspace,
)


def _write_workspace(root: Path, payload: object) -> None:
    (root / "angular.json").write_text(json.dumps(payload), encoding="utf-8")


def _workspace_payload() -> dict[str, object]:
    return {
        "version": 1,
        "projects": {
            "reports-app": {
                "projectType": "application",
                "root": "",
                "sourceRoot": "src",
                "prefix": "app",
            },
            "reports-lib": {
                "projectType": "library",
                "root": "projects/reports",
                "sourceRoot": "projects/reports/src",
            },
        },
    }


def test_should_load_typed_angular_workspace_projects(tmp_path: Path) -> None:
    _write_workspace(tmp_path, _workspace_payload())

    workspace = load_angular_workspace(tmp_path)

    assert workspace == AngularWorkspace(
        version=1,
        projects=(
            AngularProject(
                name="reports-app",
                project_type="application",
                root="",
                source_root="src",
                prefix="app",
            ),
            AngularProject(
                name="reports-lib",
                project_type="library",
                root="projects/reports",
                source_root="projects/reports/src",
                prefix=None,
            ),
        ),
    )


def test_should_reject_duplicate_angular_workspace_keys(tmp_path: Path) -> None:
    (tmp_path / "angular.json").write_text(
        '{"version":1,"version":2,"projects":{}}',
        encoding="utf-8",
    )

    with pytest.raises(AngularWorkspaceError, match="duplicate key: version"):
        load_angular_workspace(tmp_path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": 0, "projects": {}}, "version"),
        ({"version": 1, "projects": {}}, "at least one project"),
        (
            {
                "version": 1,
                "projects": {
                    "app": {
                        "projectType": "server",
                        "root": "",
                        "sourceRoot": "src",
                    }
                },
            },
            "project type",
        ),
        (
            {
                "version": 1,
                "projects": {
                    "app": {
                        "projectType": "application",
                        "root": "../app",
                        "sourceRoot": "src",
                    }
                },
            },
            "safe relative path",
        ),
        (
            {
                "version": 1,
                "projects": {
                    "app": {
                        "projectType": "application",
                        "root": "projects/app",
                        "sourceRoot": "src",
                    }
                },
            },
            "within project root",
        ),
        (
            {
                "version": 1,
                "projects": {
                    "app": {
                        "projectType": "application",
                        "root": "",
                        "sourceRoot": "src",
                        "prefix": 42,
                    }
                },
            },
            "prefix",
        ),
    ],
)
def test_should_reject_invalid_angular_workspace_boundaries(
    tmp_path: Path,
    payload: object,
    message: str,
) -> None:
    _write_workspace(tmp_path, payload)

    with pytest.raises(AngularWorkspaceError, match=message):
        load_angular_workspace(tmp_path)
