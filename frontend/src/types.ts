export type ProtocolId = "awg-legacy" | "awg" | "wireguard";
export type PeerStatus = "active" | "inactive" | "offline";
export type HealthStatus = "healthy" | "degraded" | "unavailable";

export interface Peer {
  id: string;
  name: string;
  public_key_fingerprint: string;
  ip_address: string | null;
  endpoint: string | null;
  latest_handshake: string | null;
  received_bytes: number;
  sent_bytes: number;
  persistent_keepalive: number;
  created_at: string | null;
  status: PeerStatus;
  discovered: boolean;
}

export interface ProtocolInventory {
  id: ProtocolId;
  label: string;
  container: string;
  interface: string;
  generation: "legacy" | "2.x" | "3.1" | "wireguard" | "unknown";
  health: HealthStatus;
  listen_port: number | null;
  peers: Peer[];
  warning: string | null;
}

export interface ServerInventory {
  server: {
    hostname: string;
    connection: "connected" | "degraded";
    checked_at: string;
  };
  capabilities: {
    can_read: boolean;
    can_mutate: boolean;
    can_manage_containers: boolean;
  };
  protocols: ProtocolInventory[];
}

export interface CreatedConnection {
  filename: string;
  nativeConfig: string;
  vpnUrl?: string;
}

export interface MutationPreflight {
  revision: string;
  next_ip: string | null;
  endpoint: string;
  dns: string;
}

export interface OperationResult {
  operation_id: string;
  status: string;
  peer_id?: string;
  replayed?: boolean;
  filename?: string;
  native_config?: string;
}
