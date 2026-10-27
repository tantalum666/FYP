import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

interface Digest {
  period: string;
  text_en: string;
  text_zh: string;
  polished: boolean;
  completed: number;
  check_ins: number;
}

export function DigestPanel({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [period, setPeriod] = useState<"day" | "week">("day");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    setDigest(await request<Digest>(`/digests?period=${period}`));
  }, [owner, period]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) return null;
  return (
    <section className="workspace-panel">
      <h3>{t("What happened", "这段时间发生了什么")}</h3>
      <button type="button" onClick={() => setPeriod(period === "day" ? "week" : "day")}>
        {period === "day" ? t("Show the week", "看这一周") : t("Show today", "看今天")}
      </button>
      {digest && <p>{t(digest.text_en, digest.text_zh)}</p>}
      <button
        type="button"
        onClick={() =>
          void write(`/digests/${period}/announcements`, {})
            .then(() => setNote(t("The device will speak the counts.", "设备将播报数量。")))
            .catch((reason) => setError(reason))
        }
      >
        {t("Speak the counts", "播报数量")}
      </button>
      {note && <p>{note}</p>}
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </section>
  );
}
