import { lazy, Suspense, useEffect, useId, useState } from "react";

import { createConnection, MutationApiError, mutationPreflight, operationStatus } from "../api/client";
import type { CreatedConnection, MutationPreflight, ProtocolId, ProtocolInventory } from "../types";
import { CheckIcon, CloseIcon } from "./Icons";
import { RecoveryAction } from "./RecoveryAction";

const SuccessPanel = lazy(() => import("./SuccessPanel"));

export function CreateConnectionDialog({
  hostname,
  protocols,
  initialProtocol,
  canMutate,
  onClose,
  onCreated,
}: {
  hostname: string;
  protocols: ProtocolInventory[];
  initialProtocol: ProtocolId;
  canMutate: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const nameId = useId();
  const [name, setName] = useState("Телефон");
  const [protocolId, setProtocolId] = useState(initialProtocol);
  const [keepalive, setKeepalive] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<CreatedConnection | null>(null);
  const [preflight, setPreflight] = useState<MutationPreflight | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [needsRecovery, setNeedsRecovery] = useState(false);
  const selectedProtocol = protocols.find((protocol) => protocol.id === protocolId) ?? protocols[0];
  const endpoint = `${preflight?.endpoint ?? hostname}:${selectedProtocol?.listen_port ?? "—"}`;

  useEffect(() => {
    if (!canMutate) return;
    const controller = new AbortController();
    void mutationPreflight(protocolId, controller.signal).then((value) => {
      if (!controller.signal.aborted) setPreflight(value);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : "Проверка недоступна");
        setNeedsRecovery(reason instanceof MutationApiError && reason.code === "recovery_required");
      }
    });
    return () => controller.abort();
  }, [canMutate, protocolId]);

  const close = () => { if (!submitting) onClose(); };

  async function checkStatus() {
    if (!operationId) return;
    try {
      const result = await operationStatus(protocolId, operationId);
      const labels: Record<string, string> = { committed: "Подключение создано. Если файл не получен, отзовите это подключение и создайте новое.", rolled_back: "Изменения отменены, исходная конфигурация восстановлена.", aborted: "Операция остановлена до записи.", recovery_required: "Необходимо восстановление на сервере." };
      setError(labels[result.status] ?? "Операция ещё выполняется. Проверьте позже.");
      onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Статус недоступен");
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canMutate || !name.trim() || !preflight || operationId) return;
    setSubmitting(true);
    setError(null);
    const id = crypto.randomUUID();
    setOperationId(id);
    try {
      setCreated(await createConnection({ name, protocol: protocolId, revision: preflight.revision, keepalive, operation_id: id }));
      onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Результат неизвестен. Проверьте состояние операции.");
      setNeedsRecovery(reason instanceof MutationApiError && reason.code === "recovery_required");
      onCreated();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && close()}>
      <section aria-labelledby="create-title" aria-modal="true" className="create-dialog" role="dialog">
        <button aria-label="Закрыть" className="dialog-close icon-button icon-button--plain" disabled={submitting} onClick={close} type="button"><CloseIcon size={25} /></button>
        <form className="creation-form" onSubmit={(event) => void submit(event)}>
          <h2 id="create-title">Новое подключение</h2>
          <label className="field-label" htmlFor={nameId}>Имя клиента</label>
          <input autoFocus disabled={Boolean(operationId)} id={nameId} maxLength={80} onChange={(event) => setName(event.target.value)} value={name} />

          <fieldset className="protocol-fieldset">
            <legend>Протокол</legend>
            <div className="segmented-control">
              {protocols.map((protocol) => (
                <button
                  aria-pressed={protocol.id === protocolId}
                  data-selected={protocol.id === protocolId}
                  key={protocol.id}
                  disabled={Boolean(operationId)}
                  onClick={() => { if (protocol.id !== protocolId) { setPreflight(null); setError(null); setProtocolId(protocol.id); } }}
                  type="button"
                >
                  {protocol.id === "awg" ? (protocol.generation === "3.1" ? "AWG 3.1" : "AWG 2.0") : protocol.label}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="field-label">Следующий IP-адрес</label>
          <output className="read-only-field">{preflight ? preflight.next_ip ?? "Нет свободных адресов" : canMutate ? "Проверка сервера…" : "—"}</output>

          <label className="field-label">Публичный endpoint</label>
          <output className="read-only-field read-only-field--validated">{endpoint}<CheckIcon size={19} /></output>

          <label className="checkbox-row">
            <input checked={keepalive} disabled={Boolean(operationId)} onChange={(event) => setKeepalive(event.target.checked)} type="checkbox" />
            <span>Добавить PersistentKeepalive 25</span>
          </label>

          <p className="secret-note">Приватный ключ будет показан один раз и не сохранится на сервере.</p>
          {!canMutate ? <p className="read-only-notice">Создание отключено: API запущен в безопасном режиме чтения.</p> : null}
          {error ? <p className="read-only-notice" role="alert">{error}</p> : null}
          {needsRecovery ? <RecoveryAction onRecovered={() => { onCreated(); onClose(); }} protocol={protocolId} /> : null}
          {operationId && !created && !submitting ? <button className="button button--secondary" onClick={() => void checkStatus()} type="button">Проверить состояние операции</button> : null}

          <div className="dialog-actions">
            <button className="button button--secondary" disabled={submitting} onClick={close} type="button">{created ? "Готово" : "Отмена"}</button>
            <button className="button button--primary" disabled={!canMutate || !name.trim() || !preflight?.next_ip || Boolean(operationId)} type="submit">
              {submitting ? "Создаём…" : created ? "Создано" : "Создать подключение"}
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
