import type { HealthStatus, PeerStatus } from "../types";

const labels: Record<PeerStatus, string> = {
  active: "Активен",
  inactive: "Неактивен",
  offline: "Оффлайн",
};

export function PeerStatusIndicator({ status }: { status: PeerStatus }) {
  return (
    <span className="status-indicator">
      <span className={`status-dot status-dot--${status}`} />
      {labels[status]}
    </span>
  );
}

export function HealthIndicator({ health }: { health: HealthStatus }) {
  const label = health === "healthy" ? "Готов" : health === "degraded" ? "Ограничен" : "Недоступен";
  const status = health === "healthy" ? "active" : health === "degraded" ? "inactive" : "offline";
  return (
    <span className="status-indicator status-indicator--compact">
      <span className={`status-dot status-dot--${status}`} />
      {label}
    </span>
  );
}

