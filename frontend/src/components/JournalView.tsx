import { formatDate } from "../lib/format";
import type { ServerInventory } from "../types";

export function JournalView({ inventory }: { inventory: ServerInventory }) {
  return (
    <section className="journal-view">
      <h1>Журнал</h1>
      <p>В режиме чтения журнал содержит только проверки состояния сервера.</p>
      <div className="journal-row">
        <span className="status-dot status-dot--active" />
        <strong>Состояние подключений обновлено</strong>
        <time dateTime={inventory.server.checked_at}>{formatDate(inventory.server.checked_at)}</time>
      </div>
    </section>
  );
}

