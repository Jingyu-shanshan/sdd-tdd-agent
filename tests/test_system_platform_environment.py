from pathlib import Path

from sdd_tdd_agent.platform_contract import SystemPlatformEnvironment


def test_should_read_preferred_os_release_and_clean_temporary_probe(
    tmp_path: Path,
) -> None:
    preferred = tmp_path / "etc-os-release"
    fallback = tmp_path / "usr-lib-os-release"
    preferred.write_text("ID=linuxmint\nVERSION_ID=22.1\n", encoding="utf-8")
    fallback.write_text("ID=unexpected\n", encoding="utf-8")
    environment = SystemPlatformEnvironment(
        system="linux",
        version=(3, 12, 4),
        os_release_paths=(preferred, fallback),
        temporary_root=tmp_path,
    )

    assert environment.system_name() == "linux"
    assert environment.python_version() == (3, 12, 4)
    assert environment.os_release() == "ID=linuxmint\nVERSION_ID=22.1\n"
    assert environment.temporary_directory_available() is True
    assert not tuple(tmp_path.glob("sdd-tdd-platform-*"))


def test_should_report_unavailable_system_inputs_without_raising(
    tmp_path: Path,
) -> None:
    invalid_temporary_root = tmp_path / "not-a-directory"
    invalid_temporary_root.write_text("file", encoding="utf-8")
    environment = SystemPlatformEnvironment(
        system="linux",
        version=(3, 9, 0),
        os_release_paths=(tmp_path / "missing",),
        temporary_root=invalid_temporary_root,
    )

    assert environment.os_release() is None
    assert environment.temporary_directory_available() is False
