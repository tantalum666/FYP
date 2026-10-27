import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { knowledgeCopy, nudgeLine } from "./knowledge";
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
      <h3>{t(knowledgeCopy.nudgeTitle[0], knowledgeCopy.nudgeTitle[1])}</h3>
      {!nudges.length && (
        <p className="workspace-hint">
          {t(knowledgeCopy.emptyNudges[0], knowledgeCopy.emptyNudges[1])}
        </p>
      )}
      <ul className="calibration-steps">
        {nudges.map((nudge) => {
          const line = nudgeLine(nudge);
          return (
            <li key={line.id}>
              <p>{t(line.reasonEn, line.reasonZh)}</p>
              <p>{t(line.summaryEn, line.summaryZh)}</p>
              {line.canDismiss ? (
                <button
                  className="secondary"
                  type="button"
                  onClick={() =>
                    void write(`/nudges/${line.id}/dismissals`, {})
                      .then(() => reload())
                      .catch((reason) => setError(reason))
                  }
                >
                  {t(knowledgeCopy.dismiss[0], knowledgeCopy.dismiss[1])}
                </button>
              ) : (
                <small>
                  {t(knowledgeCopy.dismissed[0], knowledgeCopy.dismissed[1])}
                </small>
              )}
            </li>
          );
        })}
      </ul>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
