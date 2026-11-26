import { useEffect, useState, type ReactNode } from "react";
import { errorText, request } from "../api";
import type { Translate } from "../types";
import type { InitiativeFinding } from "./InitiativeMessages";
import type { WorkspaceSnapshot } from "./types";

type Snapshot = NonNullable<WorkspaceSnapshot["initiative"]>;
type Result = { scope: string; rows: InitiativeFinding[]; error?: unknown };

export function InitiativeHistory({ scope, renderFinding, t }: {
  scope: string;
  renderFinding: (finding: InitiativeFinding) => ReactNode;
  t: Translate;
}) {
  const [result, setResult] = useState<Result>();
  const [attempt, retry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const invalidate = () => { controller.abort(); setResult(undefined); retry(n => n + 1); };
    window.addEventListener("desk:session", invalidate);
    window.addEventListener("desk:personal-context", invalidate);
    request<Snapshot>("/initiative?full=true", { signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      const rows = [...data.findings, ...(data.acknowledged ?? []), ...(data.history ?? []), ...(data.withdrawn ?? [])];
      rows.sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
      setResult({ scope, rows });
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ scope, rows: [], error });
    });
    return () => {
      controller.abort();
      window.removeEventListener("desk:session", invalidate);
      window.removeEventListener("desk:personal-context", invalidate);
    };
  }, [scope, attempt]);
  const shown = result?.scope === scope ? result : undefined;
  return (
    <section className="initiative-history" aria-label={t("Follow-up history", "主动跟进记录")}>
      <h3>{t("Follow-up history", "主动跟进记录")}</h3>
      {!shown ? <p role="status">{t("Loading…", "正在读取…")}</p>
        : shown.error ? <div role="alert">{errorText(shown.error, t)}{" "}
          <button className="text-button" onClick={() => retry(n => n + 1)}>{t("Retry", "重试")}</button></div>
        : shown.rows.length ? shown.rows.map(renderFinding)
        : <p>{t("No follow-ups yet.", "暂无主动跟进记录。")}</p>}
    </section>
  );
}
