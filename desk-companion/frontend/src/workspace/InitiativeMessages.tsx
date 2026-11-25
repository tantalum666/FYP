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
  withdrawn?: boolean;
  sources: { ref: string; kind: string; label: string; href?: string }[];
}

/** Contextual messages in the conversation; no approval form or separate poll. */
export function InitiativeMessage({ finding, t }: { finding: InitiativeFinding; t: Translate }) {
  const { data, offline, stale, refresh } = useWorkspace();
  const mutation = usePrivateMutation();
  const visible =
    data?.principal.kind === "owner" && data.personal_context_visible;
  const withdrawn = !!finding.withdrawn;
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
          aria-label={
            withdrawn
              ? t("Withdrawn suggestion", "已收回的建议")
              : t("Proactive suggestion", "主动建议")
          }
          key={finding.id}
        >
          {finding.created_at && <time dateTime={finding.created_at}>{new Date(finding.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>}
          <p>{t(finding.message_en, finding.message_zh)}</p>
          {withdrawn ? (
            <p role="status">
              {t(
                "Sources changed. This suggestion was withdrawn. Nothing was sent.",
                "依据已变更，这条建议已收回。没有发送。",
              )}
            </p>
          ) : (
            <details>
              <summary>
                {t("Sources", "依据")} · {finding.sources.length}
              </summary>
              <ul>
                {finding.sources.map((source) => (
                  <li key={source.ref}>{source.href?.startsWith("https://mail.google.com/mail/?") ?
                    <a href={source.href} target="_blank" rel="noreferrer">{source.label}</a> : source.label}</li>
                ))}
              </ul>
            </details>
          )}
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
