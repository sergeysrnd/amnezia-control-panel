import { lazy, Suspense, useId, useMemo, useState } from "react";

import { createDemoConnection } from "../api/client";
import type { CreatedConnection, ProtocolId, ProtocolInventory } from "../types";
import { CheckIcon, CloseIcon } from "./Icons";

const SuccessPanel = lazy(() => import("./SuccessPanel"));

export function CreateConnectionDialog({
  hostname,
  protocols,
  initialProtocol,
  canMutate,
  onClose,
}: {
  hostname: string;
  protocols: ProtocolInventory[];
  initialProtocol: ProtocolId;
  canMutate: boolean;
  onClose: () => void;
}) {
  const nameId = useId();
  const [name, setName] = useState("Телефон");
  const [protocolId, setProtocolId] = useState(initialProtocol);
  const [keepalive, setKeepalive] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<CreatedConnection | null>(null);
  const selectedProtocol = protocols.find((protocol) => protocol.id === protocolId) ?? protocols[0];
  const nextIp = useMemo(() => {
    const used = selectedProtocol?.peers.length ?? 0;
    return `10.8.${protocolId === "awg-legacy" ? 0 : protocolId === "awg" ? 1 : 2}.${used + 2}`;
  }, [protocolId, selectedProtocol?.peers.length]);
  const endpoint = `${hostname}:${selectedProtocol?.listen_port ?? "—"}`;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canMutate || !name.trim()) return;
    setSubmitting(true);
    try {
      setCreated(await createDemoConnection({ name, protocol: protocolId }));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="create-title" aria-modal="true" className="create-dialog" role="dialog">
        <button aria-label="Закрыть" className="dialog-close icon-button icon-button--plain" onClick={onClose} type="button"><CloseIcon size={25} /></button>
        <form className="creation-form" onSubmit={(event) => void submit(event)}>
          <h2 id="create-title">Новое подключение</h2>
          <label className="field-label" htmlFor={nameId}>Имя клиента</label>
          <input autoFocus id={nameId} maxLength={80} onChange={(event) => setName(event.target.value)} value={name} />

          <fieldset className="protocol-fieldset">
            <legend>Протокол</legend>
            <div className="segmented-control">
              {protocols.map((protocol) => (
                <button
                  aria-pressed={protocol.id === protocolId}
                  data-selected={protocol.id === protocolId}
                  key={protocol.id}
                  onClick={() => setProtocolId(protocol.id)}
                  type="button"
                >
                  {protocol.id === "awg" ? (protocol.generation === "3.1" ? "AWG 3.1" : "AWG 2.0") : protocol.label}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="field-label">Следующий IP-адрес</label>
          <output className="read-only-field">{nextIp}</output>

          <label className="field-label">Публичный endpoint</label>
          <output className="read-only-field read-only-field--validated">{endpoint}<CheckIcon size={19} /></output>

          <label className="checkbox-row">
            <input checked={keepalive} onChange={(event) => setKeepalive(event.target.checked)} type="checkbox" />
            <span>Добавить PersistentKeepalive 25</span>
          </label>

          <p className="secret-note">Приватный ключ будет показан один раз и не сохранится на сервере.</p>
          {!canMutate ? <p className="read-only-notice">Создание отключено: API запущен в безопасном режиме чтения.</p> : null}

          <div className="dialog-actions">
            <button className="button button--secondary" onClick={onClose} type="button">Отмена</button>
            <button className="button button--primary" disabled={!canMutate || !name.trim() || submitting} type="submit">
              {submitting ? "Создаём…" : "Создать подключение"}
            </button>
          </div>
        </form>
        {created ? (
          <Suspense fallback={<div className="success-loading">Готовим QR-код…</div>}>
            <SuccessPanel connection={created} />
          </Suspense>
        ) : (
          <aside className="creation-placeholder" aria-hidden="true">
            <div className="placeholder-lines"><span /><span /><span /></div>
            <p>После создания здесь появятся QR-код и файл конфигурации.</p>
          </aside>
        )}
      </section>
    </div>
  );
}

