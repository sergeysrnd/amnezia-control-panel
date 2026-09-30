import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from amnezia_panel.protocols import PROTOCOLS
from amnezia_panel.transport import SshDockerTransport


def test_rejects_ssh_option_as_target() -> None:
    with pytest.raises(ValueError, match="Invalid SSH target"):
        SshDockerTransport("-oProxyCommand=unexpected")


def test_rejects_non_positive_concurrency() -> None:
    with pytest.raises(ValueError, match="max_concurrency"):
        SshDockerTransport("amnezia-server", max_concurrency=0)


@pytest.mark.asyncio
async def test_rejects_non_allowlisted_path_before_execution() -> None:
    transport = SshDockerTransport("amnezia-server")

    with pytest.raises(ValueError, match="not allowlisted"):
        await transport.read_file(PROTOCOLS[0], "/etc/shadow")


@pytest.mark.asyncio
async def test_cancelled_read_reaps_ssh_process(monkeypatch) -> None:
    started = asyncio.Event()

    async def communicate():
        started.set()
        await asyncio.Event().wait()

    process = Mock(returncode=None)
    process.communicate = communicate
    process.wait = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    pending = asyncio.create_task(SshDockerTransport("amnezia-server").hostname())
    await started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_server_mode_runs_only_allowlisted_docker_read(monkeypatch) -> None:
    process = Mock(returncode=0)
    process.communicate = AsyncMock(return_value=(b"config", b""))
    execute = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", execute)
    transport = SshDockerTransport("localhost", local=True)
    spec = PROTOCOLS[0]
    assert await transport.read_file(spec, spec.config_path) == "config"
    assert execute.call_args.args == ("docker", "exec", spec.container, "cat", spec.config_path)
    with pytest.raises(ValueError, match="not allowlisted"):
        await transport.read_file(spec, "/etc/shadow")
    assert execute.await_count == 1
