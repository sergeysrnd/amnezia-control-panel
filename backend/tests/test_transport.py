import pytest

from amnezia_panel.protocols import PROTOCOLS
from amnezia_panel.transport import SshDockerTransport


def test_rejects_ssh_option_as_target() -> None:
    with pytest.raises(ValueError, match="Invalid SSH target"):
        SshDockerTransport("-oProxyCommand=unexpected")


@pytest.mark.asyncio
async def test_rejects_non_allowlisted_path_before_execution() -> None:
    transport = SshDockerTransport("amnezia-server")

    with pytest.raises(ValueError, match="not allowlisted"):
        await transport.read_file(PROTOCOLS[0], "/etc/shadow")

