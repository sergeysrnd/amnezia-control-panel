import { useEffect, useId, useState } from "react";

import { deleteConnection, MutationApiError, mutationPreflight, operationStatus } from "../api/client";
import type { MutationPreflight, Peer, ProtocolInventory } from "../types";
import { RecoveryAction } from "./RecoveryAction";

export function DeleteConnectionDialog({ peer, protocol, onClose, onDeleted }: {
  peer: Peer; protocol: ProtocolInventory; onClose: () => void; onDeleted: () => void;
}) {
  const inputId = useId();
  const [name, setName] = useState("");
  const [preflight, setPreflight] = useState<MutationPreflight | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [needsRecovery, setNeedsRecovery] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void mutationPreflight(protocol.id, controller.signal).then((result) => {
      if (!controller.signal.aborted) setPreflight(result);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : "Проверка недоступна");
        setNeedsRecovery(reason instanceof MutationApiError && reason.code === "recovery_required");
      }
    });
    return () => controller.abort();
  }, [protocol.id]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (name !== peer.name || !preflight || operationId) return;
    const id = crypto.randomUUID();
    setOperationId(id);
    setBusy(true);
    setError(null);
    try {
      const result = await deleteConnection(protocol.id, peer.id, { name, revision: preflight.revision, operation_id: id });
      if (result.status === "committed") onDeleted();
      else setError("Удаление не завершено. Проверьте состояние операции.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Результат неизвестен. Проверьте состояние операции.");
      setNeedsRecovery(reason instanceof MutationApiError && reason.code === "recovery_required");
    } finally {
      setBusy(false);
    }
  }

  async function checkStatus() {
    if (!operationId) return;
    try {
      const result = await operationStatus(protocol.id, operationId);
      if (result.status === "committed") onDeleted();
      else setError(result.status === "rolled_back" ? "Удаление отменено, доступ восстановлен." : "Операция не завершена. Требуется проверка сервера.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Статус недоступен");
    }
  }

  return (
    <div className="modal-backdrop">
      <section aria-labelledby="delete-title" aria-modal="true" className="delete-dialog" role="dialog">
        <form className="creation-form" onSubmit={(event) => void submit(event)}>
          <h2 id="delete-title">Отозвать доступ?</h2>
          <p>Подключение «{peer.name}» в {protocol.label} будет удалено. Его конфигурация перестанет работать.</p>
          <label className="field-label" htmlFor={inputId}>Введите имя клиента: {peer.name}</label>
          <input autoFocus autoComplete="off" disabled={Boolean(operationId)} id={inputId} onChange={(event) => setName(event.target.value)} value={name} />
          {!preflight && !error ? <p role="status">Проверяем конфигурацию…</p> : null}
          {error ? <p className="read-only-notice" role="alert">{error}</p> : null}
          {needsRecovery ? <RecoveryAction onRecovered={onClose} protocol={protocol.id} /> : null}
          {operationId && !busy ? <button className="button button--secondary" onClick={() => void checkStatus()} type="button">Проверить состояние операции</button> : null}
          <div className="dialog-actions">
            <button className="button button--secondary" disabled={busy} onClick={onClose} type="button">Отмена</button>
            <button className="button button--danger" disabled={!preflight || name !== peer.name || Boolean(operationId)} type="submit">{busy ? "Отзываем…" : "Отозвать доступ"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
