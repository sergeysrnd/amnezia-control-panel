import { mockInventory } from "../data/mockInventory";
import type { CreatedConnection, MutationPreflight, OperationResult, ProtocolId, ServerInventory } from "../types";

export const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";

const errors: Record<string, string> = {
  revision_conflict: "Конфигурация изменилась. Закройте форму, обновите список и повторите операцию.",
  runtime_drift: "Сохранённый конфиг и работающий интерфейс различаются. Запись заблокирована.",
  rolled_back: "Операция не применена. Исходная конфигурация и доступ восстановлены.",
  recovery_required: "Восстановление не завершено. Управление заблокировано до проверки сервера.",
  container_changed: "Контейнер изменился. Требуется повторная проверка администратором.",
  not_enrolled: "Управление этим протоколом ещё не настроено.",
  helper_unavailable: "Помощник управления недоступен. Проверьте состояние операции перед повтором.",
  busy: "Другая операция ещё выполняется. Дождитесь завершения.",
  subnet_full: "В подсети нет свободных адресов.",
  confirmation_mismatch: "Имя клиента изменилось. Обновите список и подтвердите удаление заново.",
  outcome_unknown: "Связь прервалась. Результат неизвестен: проверьте состояние операции.",
  forbidden: "Сессия устарела или запрос отклонён. Обновите страницу.",
  read_only: "Панель работает в режиме чтения.",
  operation_not_found: "Запись об операции не найдена. Обновите список подключений перед повторным созданием.",
};

export class MutationApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

export async function mutationPreflight(protocol: ProtocolId, signal?: AbortSignal): Promise<MutationPreflight> {
  if (isDemoMode) return { revision: "demo", next_ip: "10.8.0.99", endpoint: "vpn.example.com", dns: "1.1.1.1" };
  return api(`/api/v1/protocols/${protocol}/preflight`, { signal });
}

async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...options, cache: "no-store", headers: { Accept: "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { error?: string };
    throw new MutationApiError(body.error ?? "unknown", errors[body.error ?? ""] ?? `Операция не выполнена (HTTP ${response.status}). Проверьте состояние операции.`);
  }
  return response.json() as Promise<T>;
}

async function write<T>(url: string, method: string, body: unknown): Promise<T> {
  const session = await api<{ token: string | null }>("/api/v1/session");
  if (!session.token) throw new Error(errors.read_only);
  return api(url, { method, headers: { "Content-Type": "application/json", "X-Amnezia-Token": session.token }, body: JSON.stringify(body) });
}

export async function createConnection(input: {
  name: string; protocol: ProtocolId; revision: string; keepalive: boolean; operation_id: string;
}): Promise<CreatedConnection> {
  if (isDemoMode) return createDemoConnection(input);
  const { protocol, ...body } = input;
  const result = await write<OperationResult>(`/api/v1/protocols/${protocol}/peers`, "POST", body);
  if (!result.native_config || !result.filename) {
    throw new Error("Операция уже обработана. Конфигурация выдаётся один раз. Проверьте список подключений.");
  }
  return { filename: result.filename, nativeConfig: result.native_config };
}

export async function deleteConnection(protocol: ProtocolId, peerId: string, input: {
  name: string; revision: string; operation_id: string;
}): Promise<OperationResult> {
  if (isDemoMode) return { operation_id: input.operation_id, status: "committed" };
  return write(`/api/v1/protocols/${protocol}/peers/${peerId}`, "DELETE", input);
}

export async function operationStatus(protocol: ProtocolId, operationId: string): Promise<OperationResult> {
  return api(`/api/v1/protocols/${protocol}/operations/${operationId}`);
}

export async function recoverProtocol(protocol: ProtocolId): Promise<void> {
  await write(`/api/v1/protocols/${protocol}/recovery`, "POST", {});
}

export async function fetchInventory(signal?: AbortSignal): Promise<ServerInventory> {
  if (isDemoMode) {
    await delay(180, signal);
    return structuredClone(mockInventory);
  }

  const response = await fetch("/api/v1/server", {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`API вернул ${response.status}`);
  }
  return (await response.json()) as ServerInventory;
}

export async function createDemoConnection(input: {
  name: string;
  protocol: ProtocolId;
}): Promise<CreatedConnection> {
  if (!isDemoMode) {
    throw new Error("API работает в режиме чтения");
  }
  await delay(420);
  const safeName = input.name.trim().replaceAll(/[^\p{L}\p{N}_.-]+/gu, "-");
  const protocolSlug = input.protocol === "awg" ? "awg2" : input.protocol;
  return {
    filename: `${safeName || "client"}-${protocolSlug}.conf`,
    nativeConfig: "# Demonstration profile. It does not contain a real private key.\n",
    vpnUrl: `vpn://demo/${input.protocol}/${encodeURIComponent(safeName || "client")}`,
  };
}

function delay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(resolve, milliseconds);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timeout);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}
