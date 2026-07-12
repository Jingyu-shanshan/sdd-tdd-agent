import pytest

from sdd_tdd_agent.platform_contract import (
    PlatformContractError,
    parse_os_release,
)


def test_should_parse_only_required_os_release_identifiers() -> None:
    content = """\
# Operating system identity
NAME="Linux Mint"
ID="linuxmint"
VERSION_ID='22.1'
UNRELATED=value
"""

    values = parse_os_release(content)

    assert values == {"ID": "linuxmint", "VERSION_ID": "22.1"}


@pytest.mark.parametrize(
    "content",
    [
        "ID=linuxmint\nID=ubuntu\n",
        "INVALID LINE\n",
        'ID="unterminated\n',
        "ID=linux mint\n",
        'ID="linuxmint\x1b"\n',
        "id=linuxmint\n",
        "ID=\n",
    ],
)
def test_should_reject_invalid_os_release_without_echoing_content(
    content: str,
) -> None:
    with pytest.raises(PlatformContractError) as captured:
        parse_os_release(content)

    assert str(captured.value) == "Invalid os-release data"
    assert "linuxmint" not in str(captured.value)
