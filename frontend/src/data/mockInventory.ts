import type { Peer, PeerStatus, ProtocolId, ProtocolInventory, ServerInventory } from "../types";

const now = Date.now();
const statusCycle: PeerStatus[] = ["active", "active", "active", "inactive", "offline", "active", "offline"];
const handshakeMinutes = [2, 8, 1, 32, 180, 15, 2880];

function createPeer(index: number, protocolId: ProtocolId): Peer {
  const suffix = String(index + 1).padStart(2, "0");
  const status = statusCycle[index % statusCycle.length];
  const minutesAgo = handshakeMinutes[index % handshakeMinutes.length] + Math.floor(index / 7) * 11;
  return {
    id: `${protocolId}-${suffix}`,
    name: `Клиент ${suffix}`,
    public_key_fingerprint: `8f2a7c${suffix}…7d8e0f`,
    ip_address: `10.8.${protocolId === "awg-legacy" ? 0 : protocolId === "awg" ? 1 : 2}.${index + 2}`,
    endpoint: index % 5 === 4 ? null : `203.0.113.${10 + index}:${protocolId === "awg" ? 42243 : 51820}`,
    latest_handshake: status === "offline" ? new Date(now - minutesAgo * 60_000).toISOString() : new Date(now - minutesAgo * 60_000).toISOString(),
    received_bytes: (index + 1) * 128 * 1024 * 1024,
    sent_bytes: (index + 1) * 64 * 1024 * 1024,
    persistent_keepalive: index % 3 === 0 ? 25 : 0,
    created_at: `2026-08-${String((index % 24) + 1).padStart(2, "0")}T14:32:11Z`,
    status,
    discovered: index > 8 && index % 9 === 0,
  };
}

function protocol(
  id: ProtocolId,
  label: string,
  generation: ProtocolInventory["generation"],
  count: number,
  port: number,
): ProtocolInventory {
  return {
    id,
    label,
    generation,
    container: id === "awg-legacy" ? "amnezia-awg" : id === "awg" ? "amnezia-awg2" : "amnezia-wireguard",
    interface: id === "awg" ? "awg0" : "wg0",
    health: "healthy",
    listen_port: port,
    peers: Array.from({ length: count }, (_, index) => createPeer(index, id)),
    warning: null,
  };
}

export const mockInventory: ServerInventory = {
  server: {
    hostname: "panel3xui.ru",
    connection: "connected",
    checked_at: new Date().toISOString(),
  },
  capabilities: {
    can_read: true,
    can_mutate: true,
    can_manage_containers: false,
  },
  protocols: [
    protocol("awg-legacy", "AWG Legacy", "legacy", 30, 47048),
    protocol("awg", "AmneziaWG", "2.x", 17, 42243),
    protocol("wireguard", "WireGuard", "wireguard", 1, 48213),
  ],
};
