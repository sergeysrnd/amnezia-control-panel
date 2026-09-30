from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from amnezia_panel.mutation_core import MutationError
from amnezia_panel.transport import TARGET_RE


@dataclass
class MutationService:
    target: str
    local: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        if not TARGET_RE.fullmatch(self.target):
            raise ValueError("Invalid SSH target")

    async def call(self, payload: dict) -> dict:
        # Root helper holds an OS lock too, across API workers and reconnects.
        async with self._lock:
            command = ("python3", "/opt/amnezia-control/remote_helper.py")
            if not self.local:
                command = (
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=10",
                    "-o",
                    "ServerAliveInterval=15",
                    "-o",
                    "ServerAliveCountMax=3",
                    self.target,
                    *command,
                )
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(json.dumps(payload).encode()),
                    timeout=180,
                )
            except (TimeoutError, asyncio.CancelledError) as error:
                process.kill()
                await process.wait()
                raise MutationError("outcome_unknown") from error
            if process.returncode:
                raise MutationError("helper_unavailable")
            try:
                result = json.loads(stdout)
            except ValueError as error:
                raise MutationError("outcome_unknown") from error
            if not isinstance(result, dict):
                raise MutationError("outcome_unknown")
            if "error" in result:
                raise MutationError(result["error"])
            return result
