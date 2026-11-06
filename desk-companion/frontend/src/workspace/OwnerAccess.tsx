import { useState } from "react";
import type { Translate } from "../types";
import { errorText } from "../api";
import { openSession } from "../session";
import { useWorkspace } from "./WorkspaceContext";

export function OwnerAccess({ t }: { t: Translate }) {
  const { refresh } = useWorkspace();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  async function reconnect() {
    setBusy(true);
    setError(null);
    try {
      await openSession();
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="owner-access">
      <button
        className="secondary"
        disabled={busy}
        onClick={() => void reconnect()}
      >
        {busy ? t("Connecting…", "正在连接…") : t("Reconnect", "重新连接")}
      </button>
      {!!error && <p className="error-message">{errorText(error, t)}</p>}
    </div>
  );
}
