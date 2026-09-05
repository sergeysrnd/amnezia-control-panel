import { useMemo, useState } from "react";

import { AppShell, type Section } from "./components/AppShell";
import { CreateConnectionDialog } from "./components/CreateConnectionDialog";
import { JournalView } from "./components/JournalView";
import { PeerInspector } from "./components/PeerInspector";
import { PeerTable } from "./components/PeerTable";
import { PlusIcon, RefreshIcon, WarningIcon } from "./components/Icons";
import { ProtocolSwitcher } from "./components/ProtocolSwitcher";
import { useInventory } from "./hooks/useInventory";
import type { ProtocolId } from "./types";

export default function App() {
  const { data, error, loading, refreshing, refresh } = useInventory();
  const [section, setSection] = useState<Section>("overview");
  const [protocolId, setProtocolId] = useState<ProtocolId>("awg-legacy");
  const [selectedPeerId, setSelectedPeerId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const protocol = data?.protocols.find((item) => item.id === protocolId) ?? data?.protocols[0];
  const selectedPeer = useMemo(
    () => protocol?.peers.find((peer) => peer.id === selectedPeerId) ?? null,
    [protocol?.peers, selectedPeerId],
  );

  function selectProtocol(id: ProtocolId) {
    setProtocolId(id);
    setSelectedPeerId(null);
  }

  if (loading && !data) {
    return <LoadingScreen />;
  }

  if (!data) {
    return <ErrorScreen message={error ?? "Сервер недоступен"} onRetry={refresh} />;
  }

  return (
    <AppShell activeSection={section} onSectionChange={setSection}>
      <div className="workspace">
        <header className="server-header">
          <div className="server-identity"><strong>Сервер</strong><span>{data.server.hostname}</span></div>
          <div className="server-actions">
            <span className="connection-state"><span className={`status-dot status-dot--${data.server.connection === "connected" ? "active" : "inactive"}`} />{data.server.connection === "connected" ? "Подключён" : "Ограничен"}</span>
            <button aria-label="Обновить данные" className="icon-button" disabled={refreshing} onClick={refresh} type="button"><RefreshIcon className={refreshing ? "is-spinning" : ""} size={21} /></button>
          </div>
        </header>

        {section === "journal" ? <JournalView inventory={data} /> : (
          <>
            <ProtocolSwitcher onSelect={selectProtocol} protocols={data.protocols} selected={protocol?.id ?? protocolId} />
            <div className="content-with-inspector" data-inspector-open={Boolean(selectedPeer)}>
              <main className="main-content">
                <div className="content-header">
                  <div>
                    <h1>{section === "clients" ? "Все подключения" : "Подключения"}</h1>
                    {protocol?.warning ? <p className="protocol-warning"><WarningIcon size={17} />{protocol.warning}</p> : null}
                  </div>
                  <button className="button button--primary" onClick={() => setCreating(true)} type="button"><PlusIcon size={19} />Новое подключение</button>
                </div>
                {protocol ? (
                  <PeerTable onSelect={setSelectedPeerId} peers={protocol.peers} selectedPeerId={selectedPeerId} />
                ) : null}
              </main>
              {selectedPeer ? <PeerInspector onClose={() => setSelectedPeerId(null)} peer={selectedPeer} /> : null}
            </div>
          </>
        )}

        <footer className="status-footer">
          <span>Только управление подключениями</span><span aria-hidden="true">·</span><span>Контейнеры не изменяются</span>
        </footer>
      </div>
      {creating ? (
        <CreateConnectionDialog
          canMutate={data.capabilities.can_mutate}
          hostname={data.server.hostname}
          initialProtocol={protocol?.id ?? protocolId}
          onClose={() => setCreating(false)}
          protocols={data.protocols}
        />
      ) : null}
    </AppShell>
  );
}

function LoadingScreen() {
  return (
    <div className="full-screen-state" role="status">
      <div className="loading-mark">AMN</div>
      <p>Читаем состояние подключений…</p>
    </div>
  );
}

function ErrorScreen({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="full-screen-state">
      <WarningIcon size={28} />
      <h1>Не удалось подключиться</h1>
      <p>{message}</p>
      <button className="button button--primary" onClick={onRetry} type="button">Повторить</button>
    </div>
  );
}
