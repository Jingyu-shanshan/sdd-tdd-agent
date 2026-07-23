from sdd_tdd_agent.provider_registry import list_providers, render_provider_list


def test_should_list_ready_and_planned_agent_providers() -> None:
    providers = list_providers()

    assert tuple(provider.key for provider in providers) == (
        "codex",
        "custom-json",
        "claude-code",
        "cursor",
        "pi",
        "copilot",
    )
    assert providers[0].status == "adapter-ready"
    assert providers[1].status == "adapter-ready"
    assert providers[2].status == "adapter-ready"
    assert providers[3].status == "adapter-ready"
    assert providers[4].status == "adapter-ready"
    assert providers[5].status == "planned"
    assert "linux-mint" in providers[0].platforms
    assert providers[2].protocol == "claude-exec"
    assert providers[2].command == ("claude",)
    assert providers[2].install_plan is not None
    assert providers[2].install_plan.source_url == "https://claude.ai/install.sh"
    assert providers[3].protocol == "cursor-exec"
    assert providers[3].command == ("cursor-agent",)
    assert providers[3].install_plan is not None
    assert providers[3].install_plan.source_url == "https://cursor.com/install"
    assert providers[4].protocol == "pi-exec"
    assert providers[4].command == ("pi",)
    assert providers[4].install_plan is not None
    assert providers[4].install_plan.source_url == "https://pi.dev/install.sh"

    assert (
        render_provider_list(providers)
        == """\
codex: adapter-ready (macos, linux-mint) - OpenAI Codex CLI
custom-json: adapter-ready (macos, linux-mint) - Custom JSON command
claude-code: adapter-ready (macos, linux-mint) - Claude Code
cursor: adapter-ready (macos, linux-mint) - Cursor
pi: adapter-ready (macos, linux-mint) - Pi Coding Agent
copilot: planned (platform contract pending) - GitHub Copilot
"""
    )
