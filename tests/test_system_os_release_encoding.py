from pathlib import Path

from sdd_tdd_agent.platform_contract import SystemPlatformEnvironment


def test_should_ignore_unreadable_os_release_encoding(tmp_path: Path) -> None:
    invalid = tmp_path / "os-release"
    invalid.write_bytes(b"ID=linuxmint\xff\n")
    environment = SystemPlatformEnvironment(
        system="linux",
        os_release_paths=(invalid,),
        temporary_root=tmp_path,
    )

    assert environment.os_release() is None
