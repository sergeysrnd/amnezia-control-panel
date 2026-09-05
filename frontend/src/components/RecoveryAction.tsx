import { useState } from "react";

import { recoverProtocol } from "../api/client";
import type { ProtocolId } from "../types";

export function RecoveryAction({ protocol, onRecovered }: { protocol: ProtocolId; onRecovered: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function recover() {
    setBusy(true);
    try { await recoverProtocol(protocol); onRecovered(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Восстановление недоступно"); }
    finally { setBusy(false); }
  }
  return <div>
    <button className="button button--secondary" disabled={busy} onClick={() => void recover()} type="button">{busy ? "Восстанавливаем…" : "Восстановить прерванную операцию"}</button>
    {error ? <p role="alert">{error}</p> : null}
  </div>;
}
