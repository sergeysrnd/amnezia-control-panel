import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { fetchInventory } from "../api/client";
import type { ServerInventory } from "../types";

interface InventoryState {
  data: ServerInventory | null;
  error: string | null;
  loading: boolean;
  refreshing: boolean;
  refresh: () => void;
}

export function useInventory(): InventoryState {
  const [data, setData] = useState<ServerInventory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);
  const [refreshing, startTransition] = useTransition();
  const initialLoad = useRef(true);

  const refresh = useCallback(() => {
    startTransition(() => setRefreshToken((token) => token + 1));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    if (initialLoad.current) setLoading(true);

    void fetchInventory(controller.signal)
      .then((inventory) => {
        setData(inventory);
        setError(null);
        initialLoad.current = false;
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить сервер");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [refreshToken]);

  useEffect(() => {
    const interval = window.setInterval(refresh, 30_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  return { data, error, loading, refreshing, refresh };
}
