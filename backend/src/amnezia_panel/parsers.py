from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from amnezia_panel.models import PeerStatus

SECTION_RE = re.compile(r"^\s*\[([^]]+)]\s*$")
VALUE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*=\s*(.*?)\s*$")
AWG3_KEYS = frozenset(
    {
        "HeaderProtectionKey",
        "ContentPaddingAddition",
        "RekeyAfterTime",
        "RekeyTimeout",
        "RejectAfterTime",
        "KeepaliveTimeout",
        "MaxHandshakeAttempts",
        "RandomTrailers",
        "DisableCookies",
    }
)


@dataclass(frozen=True, slots=True)
class ConfigPeer:
    public_key: str
    allowed_ips: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterfaceConfig:
    listen_port: int | None
    generation: str
    peers: tuple[ConfigPeer, ...]


@dataclass(frozen=True, slots=True)
class ClientMetadata:
    name: str | None = None
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimePeer:
    public_key: str
    endpoint: str | None
    allowed_ips: tuple[str, ...]
    latest_handshake_epoch: int
    received_bytes: int
    sent_bytes: int
    persistent_keepalive: int


@dataclass(frozen=True, slots=True)
class RuntimeDump:
    listen_port: int | None
    peers: tuple[RuntimePeer, ...]


def _split_sections(config: str) -> list[tuple[str, dict[str, str]]]:
    sections: list[tuple[str, dict[str, str]]] = []
    current_name: str | None = None
    current_values: dict[str, str] = {}

    for line in config.splitlines():
        section_match = SECTION_RE.match(line)
        if section_match:
            if current_name is not None:
                sections.append((current_name, current_values))
            current_name = section_match.group(1)
            current_values = {}
            continue

        value_match = VALUE_RE.match(line)
        if value_match and current_name is not None:
            current_values[value_match.group(1)] = value_match.group(2)

    if current_name is not None:
        sections.append((current_name, current_values))
    return sections


def parse_interface_config(config: str, *, is_awg: bool) -> InterfaceConfig:
    sections = _split_sections(config)
    interface = next((values for name, values in sections if name == "Interface"), {})
    peers: list[ConfigPeer] = []

    for name, values in sections:
        if name != "Peer" or not (public_key := values.get("PublicKey")):
            continue
        allowed_ips = tuple(
            item.strip() for item in values.get("AllowedIPs", "").split(",") if item.strip()
        )
        peers.append(ConfigPeer(public_key=public_key, allowed_ips=allowed_ips))

    listen_port = _parse_optional_int(interface.get("ListenPort"))
    if not is_awg:
        generation = "wireguard"
    elif AWG3_KEYS.intersection(interface):
        generation = "3.1"
    elif interface:
        generation = "2.x"
    else:
        generation = "unknown"

    return InterfaceConfig(
        listen_port=listen_port,
        generation=generation,
        peers=tuple(peers),
    )


def parse_clients_table(raw: str) -> dict[str, ClientMetadata]:
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    metadata: dict[str, ClientMetadata] = {}
    if isinstance(parsed, list):
        records = parsed
    elif isinstance(parsed, dict):
        records = [
            {"clientId": client_id, **(value if isinstance(value, dict) else {})}
            for client_id, value in parsed.items()
        ]
    else:
        return {}

    for record in records:
        if not isinstance(record, dict):
            continue
        client_id = record.get("clientId")
        if not isinstance(client_id, str) or not client_id:
            continue
        user_data = record.get("userData")
        if not isinstance(user_data, dict):
            user_data = record
        name = user_data.get("clientName")
        created_at = user_data.get("creationDate")
        metadata[client_id] = ClientMetadata(
            name=name if isinstance(name, str) and name else None,
            created_at=created_at if isinstance(created_at, str) and created_at else None,
        )
    return metadata


def parse_runtime_dump(raw: str) -> RuntimeDump:
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        return RuntimeDump(listen_port=None, peers=())

    interface_fields = lines[0].split("\t")
    listen_port = _parse_optional_int(interface_fields[2] if len(interface_fields) > 2 else None)
    peers: list[RuntimePeer] = []
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) < 8:
            continue
        public_key = fields[0]
        if not public_key:
            continue
        peers.append(
            RuntimePeer(
                public_key=public_key,
                endpoint=None if fields[2] in {"", "(none)"} else fields[2],
                allowed_ips=tuple(item for item in fields[3].split(",") if item),
                latest_handshake_epoch=_parse_int(fields[4]),
                received_bytes=max(0, _parse_int(fields[5])),
                sent_bytes=max(0, _parse_int(fields[6])),
                persistent_keepalive=max(0, _parse_int(fields[7])),
            )
        )
    return RuntimeDump(listen_port=listen_port, peers=tuple(peers))


def opaque_peer_id(public_key: str) -> str:
    return hashlib.sha256(public_key.encode()).hexdigest()[:20]


def fingerprint(public_key: str) -> str:
    if len(public_key) <= 16:
        return public_key
    return f"{public_key[:8]}…{public_key[-6:]}"


def status_for_handshake(epoch: int, *, now: datetime | None = None) -> PeerStatus:
    if epoch <= 0:
        return PeerStatus.OFFLINE
    reference = now or datetime.now(UTC)
    age_seconds = max(0, int(reference.timestamp()) - epoch)
    if age_seconds <= 180:
        return PeerStatus.ACTIVE
    if age_seconds <= 86_400:
        return PeerStatus.INACTIVE
    return PeerStatus.OFFLINE


def datetime_from_epoch(epoch: int) -> datetime | None:
    if epoch <= 0:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC)


def first_ipv4(allowed_ips: tuple[str, ...]) -> str | None:
    return next((item.split("/", 1)[0] for item in allowed_ips if "." in item), None)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = _parse_int(value)
    return parsed if parsed > 0 else None


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
