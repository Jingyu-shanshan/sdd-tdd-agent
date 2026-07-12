from sdd_tdd_agent.provider_registry import list_providers, render_provider_list


def test_should_list_ready_and_planned_agent_providers() -> None:
    providers = list_providers()

    assert tuple(provider.key for provider in providers) == (
        "codex",
        "custom-json",
        "claude-code",
        "cursor",
        "copilot",
    )
    assert providers[0].status == "adapter-ready"
    assert providers[1].status == "adapter-ready"
    assert all(provider.status == "planned" for provider in providers[2:])
    assert "linux-mint" in providers[0].platforms

    assert (
        render_provider_list(providers)
        == """\
codex: adapter-ready (macos, linux-mint) - OpenAI Codex CLI
custom-json: adapter-ready (macos, linux-mint) - Custom JSON command
claude-code: planned (platform contract pending) - Claude Code
cursor: planned (platform contract pending) - Cursor
copilot: planned (platform contract pending) - GitHub Copilot
"""
    )
