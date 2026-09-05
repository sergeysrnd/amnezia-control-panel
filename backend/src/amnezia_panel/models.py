from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProtocolId(StrEnum):
    AWG_LEGACY = "awg-legacy"
    AWG = "awg"
    WIREGUARD = "wireguard"


class PeerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OFFLINE = "offline"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class Capabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    can_read: bool = True
    can_mutate: bool = False
    can_manage_containers: bool = False


class Peer(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    public_key_fingerprint: str
    ip_address: str | None = None
    endpoint: str | None = None
    latest_handshake: datetime | None = None
    received_bytes: int = Field(default=0, ge=0)
    sent_bytes: int = Field(default=0, ge=0)
    persistent_keepalive: int = Field(default=0, ge=0)
    created_at: str | None = None
    status: PeerStatus
    discovered: bool = False


class ProtocolInventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: ProtocolId
    label: str
    container: str
    interface: str
    generation: Literal["legacy", "2.x", "3.1", "wireguard", "unknown"]
    health: HealthStatus
    listen_port: int | None = Field(default=None, ge=1, le=65535)
    peers: tuple[Peer, ...] = ()
    warning: str | None = None


class ServerIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    hostname: str
    connection: Literal["connected", "degraded"]
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServerInventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    server: ServerIdentity
    capabilities: Capabilities = Capabilities()
    protocols: tuple[ProtocolInventory, ...]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["read-only"] = "read-only"
