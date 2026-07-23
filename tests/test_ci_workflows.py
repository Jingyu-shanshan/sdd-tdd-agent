import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = PROJECT_ROOT / ".github" / "workflows"
CHECKOUT_ACTION = "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0"
SETUP_UV_ACTION = "astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990 # v8.3.2"
QUALITY_COMMANDS = (
    "uv run ruff check .",
    "uv run ruff format --check .",
    "uv run pyright",
    "uv run pytest",
)


def _read_workflow(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


def _assert_quality_commands(workflow: str) -> None:
    for command in QUALITY_COMMANDS:
        assert command in workflow


def _assert_immutable_actions(workflow: str) -> None:
    actions = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)

    assert actions
    assert all(re.search(r"@[0-9a-f]{40}$", action) for action in actions)
    assert CHECKOUT_ACTION in workflow
    assert SETUP_UV_ACTION in workflow


def test_should_define_hosted_linux_python_quality_matrix() -> None:
    workflow = _read_workflow("ci.yml")

    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request_target:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert 'python-version: ["3.9", "3.10", "3.12"]' in workflow
    assert "uv sync --locked --dev" in workflow
    assert "uv build" in workflow
    _assert_quality_commands(workflow)
    _assert_immutable_actions(workflow)


def test_should_execute_tests_through_bash_and_zsh() -> None:
    workflow = _read_workflow("ci.yml")

    assert 'shell: ["bash", "zsh"]' in workflow
    assert "if: matrix.shell == 'zsh'" in workflow
    assert "sudo apt-get install --yes zsh" in workflow
    assert "${{ matrix.shell }} -lc 'uv run pytest'" in workflow


def test_should_require_a_manual_real_linux_mint_runner() -> None:
    workflow = _read_workflow("linux-mint.yml")

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "pull_request:" not in workflow
    assert "schedule:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: [self-hosted, linux, x64, linuxmint]" in workflow
    assert "uv run wssagent platform doctor" in workflow
    assert "Distribution: linuxmint" in workflow
    assert "Platform support: supported-target" in workflow
    assert "Readiness: ready" in workflow
    assert "sudo " not in workflow
    assert "apt-get" not in workflow
    _assert_quality_commands(workflow)
    _assert_immutable_actions(workflow)


def test_should_pin_the_uv_runtime_version() -> None:
    for name in ("ci.yml", "linux-mint.yml"):
        workflow = _read_workflow(name)

        assert 'version: "0.11.29"' in workflow
