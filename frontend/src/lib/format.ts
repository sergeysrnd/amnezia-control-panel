const relativeTime = new Intl.RelativeTimeFormat("ru", { numeric: "auto" });
const dateTime = new Intl.DateTimeFormat("ru", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  const digits = value >= 10 || exponent === 0 ? 0 : 2;
  return `${value.toFixed(digits)} ${units[exponent]}`;
}

export function formatHandshake(value: string | null): string {
  if (!value) return "Никогда";
  const milliseconds = new Date(value).getTime();
  if (!Number.isFinite(milliseconds)) return "Неизвестно";
  const seconds = Math.round((milliseconds - Date.now()) / 1000);
  if (Math.abs(seconds) < 60) return relativeTime.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return relativeTime.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 48) return relativeTime.format(hours, "hour");
  return relativeTime.format(Math.round(hours / 24), "day");
}

export function formatDate(value: string | null): string {
  if (!value) return "Неизвестно";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTime.format(parsed);
}

export function truncateEndpoint(endpoint: string | null): string {
  if (!endpoint) return "—";
  if (endpoint.length <= 24) return endpoint;
  return `${endpoint.slice(0, 13)}…${endpoint.slice(-8)}`;
}
