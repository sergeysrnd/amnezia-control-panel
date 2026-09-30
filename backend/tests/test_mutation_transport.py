import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from amnezia_panel.mutations import MutationService


@pytest.mark.asyncio
async def test_local_helper_uses_fixed_path_and_json_stdin(monkeypatch):
    process = Mock(returncode=0)
    process.communicate = AsyncMock(return_value=(b'{"status":"committed"}', b""))
    execute = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", execute)
    payload = {"action": "preflight", "protocol": "awg"}
    result = await MutationService("localhost", local=True).call(payload)
    assert result == {"status": "committed"}
    assert execute.call_args.args == ("python3", "/opt/amnezia-control/remote_helper.py")
    assert json.loads(process.communicate.call_args.args[0]) == payload
