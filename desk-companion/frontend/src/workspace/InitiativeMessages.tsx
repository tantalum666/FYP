import { useEffect } from "react";
import { useWorkspace } from "./WorkspaceContext";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import type { Translate } from "../types";

export interface InitiativeFinding {
  id: string;
  kind: string;
  message_en: string;
  message_zh: string;
  created_at?: string;
  sources: { ref: string; kind: string; label: string; href?: string }[];
}

function taskIdFromSource(source: { ref: string; kind: string }) {
  if (source.kind !== "task" || !source.ref.startsWith("task:")) return null;
  const ident = source.ref.slice("task:".length).trim();
  return ident || null;
}

/** Contextual messages in the conversation; no approval form or separate poll. */
export function InitiativeMessage({
  finding,
  t,
  onOpenTask,
}: {
  finding: InitiativeFinding;
  t: Translate;
  /** Opens the existing cited task. Does not create a follow-up or dismiss. */
  onOpenTask?: (taskId: string) => void;
}) {
  const { data, offline, stale, refresh } = useWorkspace();
  const mutation = usePrivateMutation();
  const visible =
    data?.principal.kind === "owner" && data.personal_context_visible;
  useEffect(() => {
    if (!visible) mutation.clear();
  }, [visible]);
  useEffect(() => {
    const reset = () => mutation.clear();
    window.addEventListener("desk:session", reset);
    return () => window.removeEventListener("desk:session", reset);
  }, []);
  if (!visible || offline || stale) return null;
  return (
    <>
        <article
          className="assistant-turn assistant initiative-message"
          aria-label={t("Proactive suggestion", "主动建议")}
          key={finding.id}
        >
          {finding.created_at && <time dateTime={finding.created_at}>{new Date(finding.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>}
          <p>{t(finding.message_en, finding.message_zh)}</p>
          <details>
            <summary>
              {t("Sources", "依据")} · {finding.sources.length}
            </summary>
            <ul>
              {finding.sources.map((source) => {
                const taskId = onOpenTask ? taskIdFromSource(source) : null;
                return (
                  <li key={source.ref}>
                    {source.href?.startsWith("https://mail.google.com/mail/?") ? (
                      <a href={source.href} target="_blank" rel="noreferrer">
                        {source.label}
                      </a>
                    ) : taskId && onOpenTask ? (
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => onOpenTask(taskId)}
                      >
                        {t("Open task: ", "打开待办：")}
                        {source.label}
                      </button>
                    ) : (
                      source.label
                    )}
                  </li>
                );
              })}
            </ul>
          </details>
          <button
            className="text-button"
            disabled={mutation.busy || mutation.pending}
            onClick={() =>
              void mutation.run(
                "/initiative/" + finding.id + "/dismissals",
                {},
                refresh,
              )
            }
          >
            {t("Got it", "知道了")}
          </button>
        </article>
      <MutationFeedback mutation={mutation} t={t} />
    </>
  );
}
