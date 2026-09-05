import { formatBytes, formatDate, formatHandshake } from "../lib/format";
import type { Peer } from "../types";
import { CloseIcon, CopyIcon, DownloadIcon, TrashIcon } from "./Icons";

async function copyText(value: string) {
  await navigator.clipboard.writeText(value);
}

export function PeerInspector({ peer, onClose, canMutate, onDelete }: { peer: Peer; onClose: () => void; canMutate: boolean; onDelete: () => void }) {
  return (
    <aside className="inspector" aria-label={`Сведения: ${peer.name}`}>
      <header className="inspector-header">
        <h2>{peer.name}</h2>
        <button aria-label="Закрыть сведения" className="icon-button icon-button--plain" onClick={onClose} type="button">
          <CloseIcon size={24} />
        </button>
      </header>
      <dl className="detail-list">
        <div>
          <dt>Публичный ключ</dt>
          <dd className="detail-with-action">
            <code>{peer.public_key_fingerprint}</code>
            <button aria-label="Скопировать отпечаток ключа" className="copy-button" onClick={() => void copyText(peer.public_key_fingerprint)} type="button"><CopyIcon size={18} /></button>
          </dd>
        </div>
        <div>
          <dt>Назначенный IP-адрес</dt>
          <dd>{peer.ip_address ?? "—"}</dd>
        </div>
        <div>
          <dt>Дата создания</dt>
          <dd>{formatDate(peer.created_at)}</dd>
        </div>
        <div>
          <dt>Последнее рукопожатие</dt>
          <dd>{formatHandshake(peer.latest_handshake)}</dd>
        </div>
        <div>
          <dt>Получено трафика (RX)</dt>
          <dd>{formatBytes(peer.received_bytes)}</dd>
        </div>
        <div>
          <dt>Отправлено трафика (TX)</dt>
          <dd>{formatBytes(peer.sent_bytes)}</dd>
        </div>
      </dl>
      <div className="inspector-actions">
        <button className="button button--secondary" disabled title="Приватный ключ не хранится" type="button">
          <DownloadIcon size={19} /> Скачать конфигурацию
        </button>
        <button className="danger-action" disabled={!canMutate} onClick={onDelete} title={canMutate ? "Отозвать доступ клиента" : "Недоступно в режиме чтения"} type="button">
          <TrashIcon size={19} /> Отозвать доступ
        </button>
      </div>
    </aside>
  );
}
