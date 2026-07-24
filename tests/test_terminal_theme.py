from sdd_tdd_agent.terminal_theme import InteractiveTheme


def test_should_render_readable_markdown_and_diff_colors() -> None:
    theme = InteractiveTheme(enabled=True)

    rendered = theme.markdown(
        "# Result\nUse `wssagent`.\n```diff\n-old line\n+new line\n unchanged\n```"
    )

    assert "\x1b[38;5;220m" in rendered
    assert "\x1b[38;5;159m" in rendered
    assert "\x1b[38;5;203m-old line" in rendered
    assert "\x1b[38;5;114m+new line" in rendered
    assert " unchanged" in rendered


def test_should_leave_text_plain_when_colors_are_disabled() -> None:
    text = "# Result\n```diff\n-old\n+new\n```"

    assert InteractiveTheme(enabled=False).markdown(text) == text


def test_should_style_status_roles_consistently() -> None:
    theme = InteractiveTheme(enabled=True)

    assert theme.success("done").startswith("\x1b[38;5;114m")
    assert theme.error("failed").startswith("\x1b[38;5;203m")
    assert theme.warning("review").startswith("\x1b[38;5;220m")
    assert theme.muted("details").startswith("\x1b[38;5;244m")


def test_should_render_standalone_unified_diff() -> None:
    rendered = InteractiveTheme(enabled=True).diff(
        "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new"
    )

    assert "\x1b[38;5;45m@@ -1 +1 @@" in rendered
    assert "\x1b[38;5;203m-old" in rendered
    assert "\x1b[38;5;114m+new" in rendered
