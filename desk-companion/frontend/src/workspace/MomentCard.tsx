import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { momentView, type MomentSnapshot } from "./momentView";
import { useWorkspace } from "./WorkspaceContext";

export function MomentCard({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [moments, setMoments] = useState<MomentSnapshot | null>(null);
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    setMoments(await request<MomentSnapshot>("/moments"));
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  const view = momentView(moments, !!owner);
  if (!view) return null;
  const suggestion = view.suggestion;
  return (
    <section className="today-moment" role="status">
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
      {view.paused && <p>{t(view.paused.en, view.paused.zh)}</p>}
      {view.canReset && (
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
