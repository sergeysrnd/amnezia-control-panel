import { useEffect, useState } from "react";
import { isDemoMode } from "../api/client";

interface Event { id: string; protocol: string; action: string; status: string; peer_id: string; created_at: string }
interface Journal { events: Event[]; total: number; skipped: number }
const statuses: Record<string, string> = { committed: "Выполнено", rolled_back: "Изменения отменены", aborted: "Отменено до записи", prepared: "Подготовлено", writing: "Запись", applying: "Применение", rolling_back: "Откат", recovery_required: "Требуется восстановление" };
const protocols: Record<string, string> = { "awg-legacy": "AWG Legacy", awg: "AmneziaWG", wireguard: "WireGuard" };

export function JournalView() {
  const [data, setData] = useState<Journal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const load = isDemoMode ? Promise.resolve({ events: [], total: 0, skipped: 0 }) : fetch("/api/v1/journal", { signal: controller.signal, cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error("Журнал сервера недоступен. Проверьте соединение и обновите список.");
      return response.json() as Promise<Journal>;
    });
    void load.then(value => { if (!controller.signal.aborted) setData(value); }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Не удалось загрузить журнал");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [refresh]);
  return <main className="journal-view">
    <div className="content-header"><h1>Журнал операций</h1><button className="button button--secondary" disabled={loading} onClick={() => { setLoading(true); setError(null); setRefresh(value => value + 1); }} type="button">Обновить журнал</button></div>
    <p className="section-description">Создания и отзывы через панель, их результаты и откаты. Операции официального клиента сюда не попадают.</p>
    {loading ? <p role="status">Загружаем журнал…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {data?.skipped ? <p role="alert">Не удалось прочитать записей: {data.skipped}. Остальные события показаны ниже.</p> : null}
    {data && !loading && !error && !data.events.length ? <p>{isDemoMode ? "Демо-режим: журнал сервера не загружается." : "Операций панели пока нет."}</p> : null}
    {data?.events.length ? <>
      <p className="section-description">Показано {data.events.length} из {data.total}, сначала новые. Время — начало операции, статус — её последний результат.</p>
      <div className="journal-table-wrap"><table className="journal-table"><thead><tr><th>Время</th><th>Протокол</th><th>Действие</th><th>Результат</th><th>Идентификатор клиента</th></tr></thead>
        <tbody>{data.events.map(event => <tr key={event.id}><td data-label="Время"><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString("ru-RU")}</time></td><td data-label="Протокол">{protocols[event.protocol] ?? event.protocol}</td><td data-label="Действие">{event.action === "create" ? "Создание" : "Отзыв доступа"}</td><td data-label="Результат">{statuses[event.status] ?? event.status}</td><td data-label="ID клиента"><code>{event.peer_id}</code></td></tr>)}</tbody>
      </table></div>
    </> : null}
  </main>;
}
