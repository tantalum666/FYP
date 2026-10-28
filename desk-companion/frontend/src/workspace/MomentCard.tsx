import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface Suggestion {
  id: string;
  title: string;
  reason_en: string;
  reason_zh: string;
}

interface Moments {
  suggestion: Suggestion | null;
  dismissals: Array<{ id: string }>;
  paused: boolean;
  pause_reason_en: string;
  pause_reason_zh: string;
}

export function MomentCard({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [moments, setMoments] = useState<Moments | null>(null);
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    setMoments(await request<Moments>("/moments"));
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner || !moments) return null;
  const suggestion = moments.suggestion;
  if (!suggestion && !moments.paused && !moments.dismissals.length) return null;
  return (
    <section className="connection-banner" role="status">
      {suggestion && (
        <p>
          {t(suggestion.reason_en, suggestion.reason_zh)}
          <button
            type="button"
            onClick={() =>
              void write("/moments/dismissals", { id: suggestion.id })
                .then(() => reload())
                .catch((reason) => setError(reason))
            }
          >
            {t("Not now", "现在不要")}
          </button>
        </p>
      )}
      {moments.paused && <p>{t(moments.pause_reason_en, moments.pause_reason_zh)}</p>}
      {moments.dismissals.length > 0 && (
        <button
          type="button"
          onClick={() =>
            void write("/moments/reset", {})
              .then(() => reload())
              .catch((reason) => setError(reason))
          }
        >
          {t("Reset dismissed suggestions", "清空已关闭的建议")}
        </button>
      )}
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </section>
  );
}
