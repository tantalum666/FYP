import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface Nudge {
  id: string;
  kind: string;
  state: string;
  created_at: string;
  reason_en: string;
  reason_zh: string;
  summary_en: string;
  summary_zh: string;
}

export function CheckIns({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ nudges: Nudge[] }>("/nudges");
    setNudges(next.nudges);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) return null;
  return (
    <div>
      <h3>{t("Recent check-ins", "最近的检查")}</h3>
      {!nudges.length && (
        <p className="workspace-hint">
          {t(
            "No morning briefing or evening check-in yet.",
            "还没有早晨简报或晚间检查。",
          )}
        </p>
      )}
      <ul className="calibration-steps">
        {nudges.map((nudge) => (
          <li key={nudge.id}>
            <p>{t(nudge.reason_en, nudge.reason_zh)}</p>
            <p>{t(nudge.summary_en, nudge.summary_zh)}</p>
            {nudge.state === "open" ? (
              <button
                className="secondary"
                type="button"
                onClick={() =>
                  void write(`/nudges/${nudge.id}/dismissals`, {})
                    .then(() => reload())
                    .catch((reason) => setError(reason))
                }
              >
                {t("Dismiss", "知道了")}
              </button>
            ) : (
              <small>{t("Dismissed", "已关闭")}</small>
            )}
          </li>
        ))}
      </ul>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
