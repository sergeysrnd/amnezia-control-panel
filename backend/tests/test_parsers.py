from datetime import UTC, datetime

from amnezia_panel.models import PeerStatus
from amnezia_panel.parsers import (
    fingerprint,
    parse_clients_table,
    parse_interface_config,
    parse_runtime_dump,
    status_for_handshake,
)

AWG_CONFIG = """
[Interface]
PrivateKey = secret-not-returned
Address = 10.8.0.1/24
ListenPort = 42243
Jc = 6
HeaderProtectionKey = protected

[Peer]
PublicKey = peer-public-key-a
PresharedKey = shared-secret
AllowedIPs = 10.8.0.2/32

[Peer]
PublicKey = peer-public-key-b
AllowedIPs = 10.8.0.3/32, fd00::3/128
"""


def test_parse_awg3_config_without_returning_secrets() -> None:
    result = parse_interface_config(AWG_CONFIG, is_awg=True)

    assert result.generation == "3.1"
    assert result.listen_port == 42243
    assert [peer.public_key for peer in result.peers] == [
        "peer-public-key-a",
        "peer-public-key-b",
    ]
    assert result.peers[1].allowed_ips == ("10.8.0.3/32", "fd00::3/128")
    assert not hasattr(result, "private_key")


def test_parse_clients_table_list_and_legacy_map() -> None:
    current = parse_clients_table(
        '[{"clientId":"key-a","userData":{"clientName":"Телефон",'
        '"creationDate":"2026-09-05"}}]'
    )
    legacy = parse_clients_table('{"key-b":{"clientName":"Ноутбук"}}')

    assert current["key-a"].name == "Телефон"
    assert current["key-a"].created_at == "2026-09-05"
    assert legacy["key-b"].name == "Ноутбук"


def test_parse_runtime_dump() -> None:
    raw = (
        "server-private\tserver-public\t42243\toff\n"
        "peer-a\tpsk\t203.0.113.4:51820\t10.8.0.2/32\t1725537600\t1024\t2048\t25\n"
    )

    result = parse_runtime_dump(raw)

    assert result.listen_port == 42243
    assert result.peers[0].endpoint == "203.0.113.4:51820"
    assert result.peers[0].received_bytes == 1024
    assert result.peers[0].persistent_keepalive == 25


def test_status_boundaries() -> None:
    now = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    epoch = int(now.timestamp())

    assert status_for_handshake(epoch - 180, now=now) is PeerStatus.ACTIVE
    assert status_for_handshake(epoch - 181, now=now) is PeerStatus.INACTIVE
    assert status_for_handshake(epoch - 86_401, now=now) is PeerStatus.OFFLINE
    assert status_for_handshake(0, now=now) is PeerStatus.OFFLINE


def test_fingerprint_redacts_middle() -> None:
    assert fingerprint("1234567890abcdefghijklmnop") == "12345678…klmnop"
