import { memo, useMemo, useState } from "react";

import { formatBytes, formatHandshake, truncateEndpoint } from "../lib/format";
import type { Peer } from "../types";
import { SortIcon } from "./Icons";
import { PeerStatusIndicator } from "./StatusDot";

type SortKey = "name" | "ip" | "handshake" | "traffic" | "endpoint" | "status";
type SortDirection = "asc" | "desc";

interface SortState {
  key: SortKey;
  direction: SortDirection;
}

const statusOrder = { active: 0, inactive: 1, offline: 2 } as const;

function comparable(peer: Peer, key: SortKey): string | number {
  switch (key) {
    case "name": return peer.name;
    case "ip": return peer.ip_address ?? "";
    case "handshake": return peer.latest_handshake ? new Date(peer.latest_handshake).getTime() : 0;
    case "traffic": return peer.received_bytes + peer.sent_bytes;
    case "endpoint": return peer.endpoint ?? "";
    case "status": return statusOrder[peer.status];
  }
}

const PeerRow = memo(function PeerRow({
  peer,
  selected,
  onSelect,
}: {
  peer: Peer;
  selected: boolean;
  onSelect: (peerId: string) => void;
}) {
  return (
    <tr
      aria-selected={selected}
      className="peer-row"
      data-selected={selected}
      onClick={() => onSelect(peer.id)}
    >
      <td>
        <button className="peer-name" onClick={() => onSelect(peer.id)} type="button">
          {peer.name}
          {peer.discovered ? <span className="discovered-mark" title="Найден в конфигурации">*</span> : null}
        </button>
      </td>
      <td className="numeric-cell">{peer.ip_address ?? "—"}</td>
      <td>{formatHandshake(peer.latest_handshake)}</td>
      <td className="traffic-cell">
        <span>RX&nbsp; {formatBytes(peer.received_bytes)}</span>
        <span>TX&nbsp; {formatBytes(peer.sent_bytes)}</span>
      </td>
      <td className="endpoint-cell" title={peer.endpoint ?? undefined}>{truncateEndpoint(peer.endpoint)}</td>
      <td><PeerStatusIndicator status={peer.status} /></td>
    </tr>
  );
});

const headers: { key: SortKey; label: string }[] = [
  { key: "name", label: "Клиент" },
  { key: "ip", label: "IP-адрес" },
  { key: "handshake", label: "Последнее подключение" },
  { key: "traffic", label: "Трафик" },
  { key: "endpoint", label: "Endpoint" },
  { key: "status", label: "Статус" },
];

export function PeerTable({
  peers,
  selectedPeerId,
  onSelect,
}: {
  peers: Peer[];
  selectedPeerId: string | null;
  onSelect: (peerId: string) => void;
}) {
  const [sort, setSort] = useState<SortState>({ key: "handshake", direction: "desc" });
  const sortedPeers = useMemo(() => {
    const factor = sort.direction === "asc" ? 1 : -1;
    return peers.toSorted((left, right) => {
      const a = comparable(left, sort.key);
      const b = comparable(right, sort.key);
      return typeof a === "number" && typeof b === "number"
        ? (a - b) * factor
        : String(a).localeCompare(String(b), "ru") * factor;
    });
  }, [peers, sort]);

  function changeSort(key: SortKey) {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  }

  if (peers.length === 0) {
    return <div className="empty-state">В конфигурации этого протокола нет подключений.</div>;
  }

  return (
    <div className="table-scroll" tabIndex={0} aria-label="Таблица подключений">
      <table className="peer-table">
        <thead>
          <tr>
            {headers.map((header) => {
              const active = sort.key === header.key;
              return (
                <th key={header.key} scope="col">
                  <button onClick={() => changeSort(header.key)} type="button">
                    {header.label}
                    <SortIcon direction={active ? sort.direction : "none"} />
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedPeers.map((peer) => (
            <PeerRow
              key={peer.id}
              onSelect={onSelect}
              peer={peer}
              selected={peer.id === selectedPeerId}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
