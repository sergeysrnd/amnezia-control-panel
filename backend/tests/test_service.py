import asyncio
from dataclasses import dataclass

import pytest

from amnezia_panel.models import HealthStatus, PeerStatus
from amnezia_panel.protocols import ProtocolSpec
from amnezia_panel.service import InventoryService


@dataclass
class FakeTransport:
    hostname_calls: int = 0

    async def hostname(self) -> str:
        self.hostname_calls += 1
        await asyncio.sleep(0)
        return "vpn.example.test"

    async def read_file(self, spec: ProtocolSpec, path: str) -> str:
        if path == spec.clients_table_path:
            return '[{"clientId":"peer-a","userData":{"clientName":"Телефон"}}]'
        return (
            "[Interface]\nListenPort = 51820\n\n"
            "[Peer]\nPublicKey = peer-a\nAllowedIPs = 10.8.0.2/32\n"
        )

    async def runtime_dump(self, spec: ProtocolSpec) -> str:
        return "private\tpublic\t51820\toff\npeer-a\tpsk\t(none)\t10.8.0.2/32\t0\t0\t0\t0\n"


@pytest.mark.asyncio
async def test_inventory_is_read_only_and_merges_metadata() -> None:
    transport = FakeTransport()
    inventory = await InventoryService(transport).inventory()

    assert inventory.server.hostname == "vpn.example.test"
    assert inventory.capabilities.can_mutate is False
    assert all(protocol.health is HealthStatus.HEALTHY for protocol in inventory.protocols)
    assert inventory.protocols[0].peers[0].name == "Телефон"
    assert inventory.protocols[0].peers[0].status is PeerStatus.OFFLINE
    assert inventory.protocols[0].peers[0].public_key_fingerprint == "peer-a"


@pytest.mark.asyncio
async def test_concurrent_inventory_requests_share_one_refresh() -> None:
    transport = FakeTransport()
    service = InventoryService(transport, cache_ttl_seconds=5)

    inventories = await asyncio.gather(*(service.inventory() for _ in range(6)))

    assert transport.hostname_calls == 1
    assert all(inventory is inventories[0] for inventory in inventories)


@pytest.mark.asyncio
async def test_invalidation_during_refresh_does_not_cache_stale_inventory() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingTransport(FakeTransport):
        async def hostname(self) -> str:
            self.hostname_calls += 1
            started.set()
            await release.wait()
            return "vpn.example.test"

    transport = BlockingTransport()
    service = InventoryService(transport, cache_ttl_seconds=60)
    pending = asyncio.create_task(service.inventory())
    await started.wait()
    service.invalidate()
    release.set()
    await pending
    await service.inventory()
    assert transport.hostname_calls == 2
