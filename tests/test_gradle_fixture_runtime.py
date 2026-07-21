from pathlib import Path


GRADLE_BUILD = (
    Path(__file__).parent / "fixtures" / "toolchains" / "gradle" / "build.gradle.kts"
)


def test_should_include_junit_platform_launcher_at_runtime() -> None:
    build = GRADLE_BUILD.read_text(encoding="utf-8")

    assert (
        'testRuntimeOnly("org.junit.platform:junit-platform-launcher:6.1.2")' in build
    )
