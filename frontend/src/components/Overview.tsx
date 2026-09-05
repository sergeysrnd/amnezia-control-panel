import type { ProtocolId, ServerInventory } from "../types";

export function Overview({ inventory, onOpen }: { inventory: ServerInventory; onOpen: (id: ProtocolId) => void }) {
  const peers = inventory.protocols.flatMap((protocol) => protocol.peers);
  const active = peers.filter((peer) => peer.status === "active").length;
  const healthy = inventory.protocols.filter((protocol) => protocol.health === "healthy").length;
  return <main className="overview-view">
    <h1>Обзор сервера</h1>
    <p className="section-description">Состояние протоколов и подключений на одном экране.</p>
    <div className="summary-grid">
      <div className="summary-card"><span>Всего подключений</span><strong>{peers.length}</strong></div>
      <div className="summary-card"><span>Недавно активны</span><strong>{active}</strong><small>Рукопожатие за последние 3 минуты</small></div>
      <div className="summary-card"><span>Протоколы доступны</span><strong>{healthy} / {inventory.protocols.length}</strong></div>
    </div>
    <h2>Протоколы</h2>
    <div className="protocol-card-grid">{inventory.protocols.map((protocol) => <article className="protocol-card" key={protocol.id}>
      <h3>{protocol.id === "awg" ? `AWG ${protocol.generation === "3.1" ? "3.1" : "2.0"}` : protocol.label}</h3>
      <p>{protocol.health === "healthy" ? "Доступен" : protocol.health === "degraded" ? "Требует внимания" : "Недоступен"}</p>
      <dl><div><dt>Подключений</dt><dd>{protocol.peers.length}</dd></div><div><dt>UDP-порт</dt><dd>{protocol.listen_port ?? "—"}</dd></div></dl>
      {protocol.warning ? <p className="protocol-warning">{protocol.warning}</p> : null}
      <button className="button button--secondary" onClick={() => onOpen(protocol.id)} type="button">Открыть клиентов {protocol.label}</button>
    </article>)}</div>
    <p className="section-description">Статистика относится к последнему полученному состоянию сервера. Управление подключениями — в разделе «Клиенты».</p>
  </main>;
}
