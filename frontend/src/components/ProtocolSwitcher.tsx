import type { ProtocolId, ProtocolInventory } from "../types";

function protocolLabel(protocol: ProtocolInventory): string {
  if (protocol.id === "awg") {
    return protocol.generation === "3.1" ? "AWG 3.1" : "AWG 2.0";
  }
  return protocol.label;
}

export function ProtocolSwitcher({
  protocols,
  selected,
  onSelect,
}: {
  protocols: ProtocolInventory[];
  selected: ProtocolId;
  onSelect: (id: ProtocolId) => void;
}) {
  return (
    <div className="protocol-switcher" role="tablist" aria-label="VPN-протокол">
      {protocols.map((protocol) => (
        <button
          aria-selected={protocol.id === selected}
          className="protocol-tab"
          data-active={protocol.id === selected}
          key={protocol.id}
          onClick={() => onSelect(protocol.id)}
          role="tab"
          type="button"
        >
          <span>{protocolLabel(protocol)}</span>
          <strong>{protocol.peers.length}</strong>
        </button>
      ))}
    </div>
  );
}

