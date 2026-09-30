from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from amnezia_panel.models import (
    HealthStatus,
    Peer,
    ProtocolId,
    ProtocolInventory,
    ServerIdentity,
    ServerInventory,
)
from amnezia_panel.parsers import (
    ClientMetadata,
    ConfigPeer,
    datetime_from_epoch,
    fingerprint,
    first_ipv4,
    opaque_peer_id,
    parse_clients_table,
    parse_interface_config,
    parse_runtime_dump,
    status_for_handshake,
)
from amnezia_panel.protocols import PROTOCOLS, ProtocolSpec
from amnezia_panel.transport import DockerTransport, TransportError


class InventoryService:
    def __init__(self, transport: DockerTransport, *, cache_ttl_seconds: float = 5.0) -> None:
        self._transport = transport
        self._cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._cached_inventory: ServerInventory | None = None
        self._cache_expires_at = 0.0
        self._refresh_lock = asyncio.Lock()
        self._cache_generation = 0

    def invalidate(self) -> None:
        self._cache_generation += 1
        self._cache_expires_at = 0.0

    async def inventory(self) -> ServerInventory:
        now = time.monotonic()
        if self._cached_inventory is not None and now < self._cache_expires_at:
            return self._cached_inventory

        async with self._refresh_lock:
            now = time.monotonic()
            if self._cached_inventory is not None and now < self._cache_expires_at:
                return self._cached_inventory
            generation = self._cache_generation
            inventory = await self._load_inventory()
            self._cached_inventory = inventory
            self._cache_expires_at = (
                time.monotonic() + self._cache_ttl_seconds
                if generation == self._cache_generation
                else 0.0
            )
            return inventory

    async def _load_inventory(self) -> ServerInventory:
        hostname_task = asyncio.create_task(self._transport.hostname())
        protocol_tasks = [asyncio.create_task(self._inspect(spec)) for spec in PROTOCOLS]
        hostname_result, *protocol_results = await asyncio.gather(
            hostname_task, *protocol_tasks, return_exceptions=True
        )

        hostname = (
            hostname_result
            if isinstance(hostname_result, str) and hostname_result
            else "Недоступный сервер"
        )
        protocols = tuple(
            result
            if isinstance(result, ProtocolInventory)
            else self._unavailable(spec, str(result))
            for spec, result in zip(PROTOCOLS, protocol_results, strict=True)
        )
        connection = (
            "connected"
            if isinstance(hostname_result, str)
            and any(protocol.health is not HealthStatus.UNAVAILABLE for protocol in protocols)
            else "degraded"
        )
        return ServerInventory(
            server=ServerIdentity(hostname=hostname, connection=connection),
            protocols=protocols,
        )

    async def _inspect(self, spec: ProtocolSpec) -> ProtocolInventory:
        config_result, metadata_result, runtime_result = await asyncio.gather(
            self._transport.read_file(spec, spec.config_path),
            self._transport.read_file(spec, spec.clients_table_path),
            self._transport.runtime_dump(spec),
            return_exceptions=True,
        )
        if isinstance(config_result, Exception):
            raise TransportError(f"Config unavailable: {config_result}")

        is_awg = spec.id is not ProtocolId.WIREGUARD
        config = parse_interface_config(config_result, is_awg=is_awg)
        generation = "legacy" if spec.id is ProtocolId.AWG_LEGACY else config.generation

        metadata = (
            parse_clients_table(metadata_result) if isinstance(metadata_result, str) else {}
        )
        runtime = parse_runtime_dump(runtime_result) if isinstance(runtime_result, str) else None
        peers = self._merge_peers(config.peers, metadata, runtime.peers if runtime else ())
        warning = None
        health = HealthStatus.HEALTHY
        if runtime is None:
            health = HealthStatus.DEGRADED
            warning = "Runtime-статистика временно недоступна"
        elif isinstance(metadata_result, Exception):
            health = HealthStatus.DEGRADED
            warning = "Имена клиентов временно недоступны"

        return ProtocolInventory(
            id=spec.id,
            label=spec.label,
            container=spec.container,
            interface=spec.interface,
            generation=generation,  # type: ignore[arg-type]
            health=health,
            listen_port=(runtime.listen_port if runtime else None) or config.listen_port,
            peers=peers,
            warning=warning,
        )

    @staticmethod
    def _merge_peers(
        config_peers: tuple[ConfigPeer, ...],
        metadata: dict[str, ClientMetadata],
        runtime_peers: tuple,
    ) -> tuple[Peer, ...]:
        runtime_by_key = {peer.public_key: peer for peer in runtime_peers}
        now = datetime.now(UTC)
        peers: list[Peer] = []
        for index, config_peer in enumerate(config_peers, start=1):
            runtime = runtime_by_key.get(config_peer.public_key)
            client_metadata = metadata.get(config_peer.public_key)
            allowed_ips = runtime.allowed_ips if runtime else config_peer.allowed_ips
            handshake_epoch = runtime.latest_handshake_epoch if runtime else 0
            peers.append(
                Peer(
                    id=opaque_peer_id(config_peer.public_key),
                    name=(client_metadata.name if client_metadata else None)
                    or f"Обнаруженный клиент {index:02d}",
                    public_key_fingerprint=fingerprint(config_peer.public_key),
                    ip_address=first_ipv4(allowed_ips),
                    endpoint=runtime.endpoint if runtime else None,
                    latest_handshake=datetime_from_epoch(handshake_epoch),
                    received_bytes=runtime.received_bytes if runtime else 0,
                    sent_bytes=runtime.sent_bytes if runtime else 0,
                    persistent_keepalive=runtime.persistent_keepalive if runtime else 0,
                    created_at=client_metadata.created_at if client_metadata else None,
                    status=status_for_handshake(handshake_epoch, now=now),
                    discovered=client_metadata is None,
                )
            )
        return tuple(peers)

    @staticmethod
    def _unavailable(spec: ProtocolSpec, message: str) -> ProtocolInventory:
        safe_message = "Контейнер или интерфейс недоступен"
        if "No such container" not in message and "No such device" not in message:
            safe_message = "Не удалось прочитать состояние протокола"
        generation = "wireguard" if spec.id is ProtocolId.WIREGUARD else "unknown"
        return ProtocolInventory(
            id=spec.id,
            label=spec.label,
            container=spec.container,
            interface=spec.interface,
            generation=generation,  # type: ignore[arg-type]
            health=HealthStatus.UNAVAILABLE,
            warning=safe_message,
        )
