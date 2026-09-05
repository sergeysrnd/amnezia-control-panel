from dataclasses import dataclass

import pytest

from amnezia_panel.models import HealthStatus, PeerStatus
from amnezia_panel.protocols import ProtocolSpec
from amnezia_panel.service import InventoryService


@dataclass
class FakeTransport:
    async def hostname(self) -> str:
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
    inventory = await InventoryService(FakeTransport()).inventory()

    assert inventory.server.hostname == "vpn.example.test"
    assert inventory.capabilities.can_mutate is False
    assert all(protocol.health is HealthStatus.HEALTHY for protocol in inventory.protocols)
    assert inventory.protocols[0].peers[0].name == "Телефон"
    assert inventory.protocols[0].peers[0].status is PeerStatus.OFFLINE
    assert inventory.protocols[0].peers[0].public_key_fingerprint == "peer-a"
