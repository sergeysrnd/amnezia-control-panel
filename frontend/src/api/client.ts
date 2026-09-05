import { mockInventory } from "../data/mockInventory";
import type { CreatedConnection, ProtocolId, ServerInventory } from "../types";

const demoMode = import.meta.env.VITE_DEMO_MODE === "true";

export async function fetchInventory(signal?: AbortSignal): Promise<ServerInventory> {
  if (demoMode) {
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
  if (!demoMode) {
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
