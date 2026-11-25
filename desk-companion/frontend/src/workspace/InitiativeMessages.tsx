import { useEffect, useRef } from "react";
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
  notice_id?: string | null;
  sources: { ref: string; kind: string; label: string; href?: string }[];
}

export function findingMatchesNotice(
  finding: InitiativeFinding,
  noticeId?: string | null,
) {
  if (!noticeId) return false;
  if (finding.notice_id && finding.notice_id === noticeId) return true;
  return noticeId === "insight-" + finding.id;
}

/** Contextual messages in the conversation; no approval form or separate poll. */
export function InitiativeMessage({
  finding,
  t,
  focusNoticeId,
  onFocused,
}: {
  finding: InitiativeFinding;
  t: Translate;
  /** Inbox notice id that should open this finding’s Sources. */
  focusNoticeId?: string | null;
  onFocused?: () => void;
}) {
  const { data, offline, stale, refresh } = useWorkspace();
  const mutation = usePrivateMutation();
  const cardRef = useRef<HTMLElement | null>(null);
  const detailsRef = useRef<HTMLDetailsElement | null>(null);
  const focused = findingMatchesNotice(finding, focusNoticeId);
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
  useEffect(() => {
    if (!focused || !visible || offline || stale) return;
    const details = detailsRef.current;
    const card = cardRef.current;
    if (details) details.open = true;
    card?.scrollIntoView({ block: "nearest" });
    card?.focus();
    onFocused?.();
  }, [focused, visible, offline, stale, finding.id]);
  if (!visible || offline || stale) return null;
  return (
    <>
        <article
          ref={cardRef}
          className="assistant-turn assistant initiative-message"
          aria-label={t("Proactive suggestion", "主动建议")}
          data-finding-id={finding.id}
          tabIndex={focused ? -1 : undefined}
          key={finding.id}
        >
          {finding.created_at && <time dateTime={finding.created_at}>{new Date(finding.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>}
          <p>{t(finding.message_en, finding.message_zh)}</p>
          <details ref={detailsRef}>
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
