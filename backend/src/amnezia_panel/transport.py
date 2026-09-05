from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol

from amnezia_panel.protocols import ProtocolSpec

TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,254}$")


class TransportError(RuntimeError):
    """Raised when a read-only transport command fails."""


class DockerTransport(Protocol):
    async def read_file(self, spec: ProtocolSpec, path: str) -> str: ...

    async def runtime_dump(self, spec: ProtocolSpec) -> str: ...

    async def hostname(self) -> str: ...


@dataclass(frozen=True, slots=True)
class SshDockerTransport:
    target: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not TARGET_RE.fullmatch(self.target):
            raise ValueError("Invalid SSH target")

    async def read_file(self, spec: ProtocolSpec, path: str) -> str:
        if path not in {spec.config_path, spec.clients_table_path}:
            raise ValueError("Path is not allowlisted for this protocol")
        return await self._run_remote("docker", "exec", spec.container, "cat", path)

    async def runtime_dump(self, spec: ProtocolSpec) -> str:
        return await self._run_remote(
            "docker",
            "exec",
            spec.container,
            spec.binary,
            "show",
            spec.interface,
            "dump",
        )

    async def hostname(self) -> str:
        return (await self._run_remote("hostname", "-f")).strip()

    async def _run_remote(self, *command: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={max(1, int(self.timeout_seconds))}",
            self.target,
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise TransportError("Remote read timed out") from error
        if process.returncode != 0:
            message = stderr.decode(errors="replace").strip()
            raise TransportError(message or "Remote read failed")
        return stdout.decode(errors="strict")
