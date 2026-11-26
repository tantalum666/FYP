import { findingMatchesNotice, findingSource, canActOnFinding } from "./findingNavigation";
import { useEffect, useRef } from "react";
import { useWorkspace } from "./WorkspaceContext";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import type { Translate } from "../types";

export interface InitiativeFollowupStatus {
  task_id: string;
  title: string;
  status: string;
  open: boolean;
  bound_at?: string;
}

export interface InitiativeFinding {
  id: string;
  kind: string;
  message_en: string;
  message_zh: string;
  created_at?: string;
  withdrawn?: boolean;
  historical?: boolean;
  acknowledged?: boolean;
  notice_id?: string | null;
  sources: { ref: string; kind: string; label: string; href?: string }[];
  followup_status?: InitiativeFollowupStatus | null;
}

function followupLabel(status: InitiativeFollowupStatus, t: Translate) {
  if (status.status === "missing")
    return t(
      "The follow-up task is no longer available. Nothing was sent.",
      "跟进事务已不可用。没有发送。",
    );
  if (status.status === "completed")
    return t("Follow-up completed. Nothing was sent.", "跟进已完成。没有发送。");
  if (status.status === "cancelled")
    return t("Follow-up cancelled. Nothing was sent.", "跟进已取消。没有发送。");
  if (status.status === "waiting")
    return t("Follow-up waiting. Nothing was sent.", "跟进仍在等待。没有发送。");
  return t("Follow-up open. Nothing was sent.", "跟进仍在进行。没有发送。");
}

/** Contextual messages in the conversation; no approval form or separate poll. */
export function InitiativeMessage({
  finding, readOnly = false,
  t,
  onOpenTask, onOpenMemory, onOpenCalendar, focusNoticeId, onFocused, expandedSources, onSourcesChange,
}: {
  finding: InitiativeFinding;
  readOnly?: boolean;
  t: Translate;
  /** Opens the existing cited task. Does not create a follow-up or dismiss. */
  onOpenTask?: (taskId: string) => void;
  onOpenMemory?: (id: string) => void;
  onOpenCalendar?: (ref: string) => void;
  focusNoticeId?: string;
  onFocused?: () => void;
  expandedSources: boolean;
  onSourcesChange: (id:string,open:boolean) => void;
}) {
  const { data, offline, stale, refresh } = useWorkspace();
  const mutation = usePrivateMutation();
  const cardRef = useRef<HTMLElement | null>(null);
  const detailsRef = useRef<HTMLDetailsElement | null>(null);
  const focused = findingMatchesNotice(finding, focusNoticeId);
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
  useEffect(() => {
    if (!focused || !visible || offline || stale) return;
    const details = detailsRef.current;
    const card = cardRef.current;
    onSourcesChange(finding.id,true);
    if (details) details.open = true;
    card?.scrollIntoView({ block: "nearest" });
    card?.focus();
    onFocused?.();
  }, [focused, visible, offline, stale, finding.id]);
  if (!visible || offline || stale) return null;
  const followup = finding.followup_status;
  const actionable = canActOnFinding(finding);
  return (
    <>
        <article
          ref={cardRef}
          className="assistant-turn assistant initiative-message"
          data-finding-id={finding.id}
          tabIndex={focused ? -1 : undefined}
          aria-label={finding.acknowledged ? t("Acknowledged suggestion", "已知晓的跟进") : withdrawn ? t("Withdrawn suggestion", "已收回的建议") : t("Proactive suggestion", "主动建议")}
          key={finding.id}
        >
          {finding.created_at && <time dateTime={finding.created_at}>{new Date(finding.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time>}
          {finding.acknowledged && <small className="finding-acknowledged">{t("Acknowledged", "已知晓")}</small>}
          <p>{withdrawn ? t("Sources changed. This suggestion was withdrawn.", "依据已变更，这条建议已收回。") : t(finding.message_en, finding.message_zh)}</p>
          {!withdrawn && <details ref={detailsRef} open={expandedSources} onToggle={event=>{ const open=event.currentTarget.open; if(open!==expandedSources)onSourcesChange(finding.id,open); }}>
            <summary>
              {t("Sources", "依据")} · {finding.sources.length}
            </summary>
            <ul>
              {finding.sources.map((source) => {
                const target = findingSource(source);
                const taskId = target?.page === "tasks" && target.itemId;
                const memoryId = target?.page === "memory" && target.itemId;
                const calendarRef = target?.page === "calendar" && target.itemId;
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
                    ) : memoryId && onOpenMemory ? (
                      <button type="button" className="text-button" onClick={() => onOpenMemory(memoryId)}>
                        {t("Open memory: ", "打开记忆：")}{source.label}
                      </button>
                    ) : calendarRef && onOpenCalendar ? (
                      <button type="button" className="text-button" onClick={() => onOpenCalendar(calendarRef)}>
                        {t("Open calendar: ", "打开日程：")}{source.label}
                      </button>
                    ) : (
                      source.label
                    )}
                  </li>
                );
              })}
            </ul>
          </details>}
          {actionable && followup && (
            <p role="status">
              {followupLabel(followup, t)}
              {followup.title ? ` · ${followup.title}` : ""}
            </p>
          )}
          {!readOnly && !finding.acknowledged && <div className="workspace-inline-actions">
            {actionable && !followup && (
              <button
                className="primary"
                disabled={mutation.busy || mutation.pending}
                onClick={() =>
                  void mutation.run("/initiative/" + finding.id + "/follow-ups", {}, refresh)
                }
              >
                {t("Follow up on this", "据此跟进")}
              </button>
            )}
            {actionable && (
              <button
                className="text-button"
                disabled={mutation.busy || mutation.pending}
                onClick={() =>
                  void mutation.run(
                    "/initiative/" + finding.id + "/snoozes",
                    { minutes: 60 },
                    refresh,
                  )
                }
              >
                {t("Remind me later", "稍后再提醒")}
              </button>
            )}
            <button
              className="text-button"
              disabled={mutation.busy || mutation.pending}
              onClick={() =>
                void mutation.run("/initiative/" + finding.id + "/dismissals", {}, refresh)
              }
            >
              {t("Got it", "知道了")}
            </button>
          </div>}
        </article>
      <MutationFeedback mutation={mutation} t={t} />
    </>
  );
}
