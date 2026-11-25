import { useEffect, useState } from "react";
import { request } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import "./mail-followups.css";

export const LOCAL_REPLY_DRAFT =
  "Thanks for the update. I have not sent this reply.";

export interface MailReplyDraft {
  id: string;
  body: string;
  summary: string;
  fingerprint: string;
  expires_at: string;
  send: false;
}

export interface MailReplyReminder {
  id: string;
  task_id: string;
  task_title: string;
  fingerprint: string;
  observation_revision: number;
  summary: string;
  message_ids: string[];
  source_label: string;
  live_mailbox: false;
  count: number;
  draft_state: "none" | "pending" | "saved";
  draft: MailReplyDraft | null;
}

export function reminderIsLocal(reminder: MailReplyReminder) {
  return reminder.source_label.startsWith("Local mail sample");
}

export function MailReplyReminderCard({
  reminder,
  t,
  drafting,
  draftText,
  original,
  note,
  busy,
  onRead,
  onReread,
  onStartDraft,
  onDraftText,
  onReview,
  onDismiss,
  onDecide,
}: {
  reminder: MailReplyReminder;
  t: Translate;
  drafting: boolean;
  draftText: string;
  original: string;
  note: string;
  busy: boolean;
  onRead: () => void;
  onReread: () => void;
  onStartDraft: () => void;
  onDraftText: (value: string) => void;
  onReview: () => void;
  onDismiss: () => void;
  onDecide: (action: "confirm" | "cancel") => void;
}) {
  const messageId = reminder.message_ids[reminder.message_ids.length - 1];
  return (
    <article className="assistant-action-card mail-reply-reminder" aria-label={t("Followed email reminder", "跟进邮件提醒")}>
      <span className="workspace-eyebrow">{t("One reply on this task", "这件事务有一封新回复")}</span>
      <h3>{reminder.task_title}</h3>
      <p>{reminder.summary}</p>
      <small>
        {reminder.source_label}
        {reminder.live_mailbox ? "" : ""}
      </small>
      {!!note && <p role="status">{note}</p>}
      {!!original && (
        <blockquote>
          <small>{t("Original message. Not saved as a memory.", "邮件原文。不会存成记忆。")}</small>
          <p>{original}</p>
        </blockquote>
      )}
      {reminder.draft?.send === false && (
        <div>
          <p>{t("Review this draft. Saving it does not send the email.", "请核对这份草稿。保存不会发送邮件。")}</p>
          <p>
            <strong>{reminder.draft.summary}</strong>
          </p>
          <blockquote>{reminder.draft.body}</blockquote>
          <div className="workspace-inline-actions">
            <button className="primary" disabled={busy} onClick={() => onDecide("confirm")}>
              {t("Save draft", "保存草稿")}
            </button>
            <button className="secondary" disabled={busy} onClick={() => onDecide("cancel")}>
              {t("Discard draft", "放弃草稿")}
            </button>
          </div>
        </div>
      )}
      {reminder.draft_state === "saved" && !reminder.draft && (
        <p>{t("Draft saved. Nothing was sent.", "草稿已保存。没有发送。")}</p>
      )}
      {drafting && !reminder.draft && (
        <label>
          {t("Reply draft", "回复草稿")}
          <textarea value={draftText} onChange={(event) => onDraftText(event.target.value)} />
        </label>
      )}
      <div className="workspace-inline-actions">
        <button className="secondary" disabled={busy || !messageId} onClick={onRead}>
          {t("Read the message", "阅读原文")}
        </button>
        <button className="secondary" disabled={busy} onClick={onReread}>
          {t("Check again", "再次核对")}
        </button>
        {!drafting && !reminder.draft && reminder.draft_state !== "saved" && (
          <button className="primary" disabled={busy} onClick={onStartDraft}>
            {t("Draft a reply", "拟一封回复")}
          </button>
        )}
        {drafting && !reminder.draft && (
          <button className="primary" disabled={busy || !draftText.trim()} onClick={onReview}>
            {t("Review draft", "核对草稿")}
          </button>
        )}
        <button className="text-button" disabled={busy} onClick={onDismiss}>
          {t("Not now", "暂时不用")}
        </button>
      </div>
    </article>
  );
}

export function MailReplyReminders({
  t,
  taskId,
}: {
  t: Translate;
  taskId?: string;
}) {
  const { data, offline, stale } = useWorkspace();
  const visible = data?.principal.kind === "owner" && !!data.personal_context_visible && !offline && !stale;
  const [rows, setRows] = useState<MailReplyReminder[]>([]);
  const [drafting, setDrafting] = useState<string | null>(null);
  const [draftText, setDraftText] = useState(LOCAL_REPLY_DRAFT);
  const [original, setOriginal] = useState<Record<string, string>>({});
  const [note, setNote] = useState<Record<string, string>>({});
  const mutation = usePrivateMutation();
  useEffect(() => {
    if (!visible) {
      setRows([]);
      return;
    }
    let live = true;
    const load = () => {
      const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
      void request<{ reminders: MailReplyReminder[] }>(`/mail-followups/reminders${query}`)
        .then((reply) => {
          if (live) setRows(reply.reminders);
        })
        .catch(() => {
          if (live) setRows([]);
        });
    };
    load();
    window.addEventListener("desk:mail-reply", load);
    return () => {
      live = false;
      window.removeEventListener("desk:mail-reply", load);
    };
  }, [visible, taskId, data?.personal_context_visible]);
  if (!visible || !rows.length) return null;
  function changed() {
    window.dispatchEvent(new Event("desk:mail-reply"));
  }
  return (
    <div className="mail-reply-reminders">
      {rows.map((reminder) => (
        <MailReplyReminderCard
          key={reminder.id}
          reminder={reminder}
          t={t}
          drafting={drafting === reminder.id}
          draftText={draftText}
          original={original[reminder.id] ?? ""}
          note={note[reminder.id] ?? ""}
          busy={mutation.busy || mutation.pending}
          onRead={() => {
            const messageId = reminder.message_ids[reminder.message_ids.length - 1];
            void mutation.run<{ read_state?: string; message?: { body?: string; subject?: string }; error?: string }>(
              `/mail-followups/${reminder.id}/reads`,
              { message_id: messageId },
              (result) => {
                if (result.read_state === "read" && result.message) {
                  setOriginal((old) => ({ ...old, [reminder.id]: result.message?.body || result.message?.subject || "" }));
                  setNote((old) => ({
                    ...old,
                    [reminder.id]: t(
                      "Opened the original message. It was not saved as a memory, and nothing was sent.",
                      "已打开原文。没有存成记忆，也没有发送。",
                    ),
                  }));
                } else {
                  setNote((old) => ({
                    ...old,
                    [reminder.id]: t(
                      "The message could not be read. That is not a confirmed new reply, and nothing was sent.",
                      "邮件没有读成。这不是一次已确认的新回复，也没有发送。",
                    ),
                  }));
                }
              },
            );
          }}
          onReread={() => {
            void mutation.run<{ state?: string; sent?: boolean }>(
              `/mail-followups/${reminder.id}/reread`,
              {},
              (result) => {
                const failed = result.state === "failed" || result.state === "unavailable";
                const unknown = result.state === "unknown";
                setNote((old) => ({
                  ...old,
                  [reminder.id]: unknown
                    ? t(
                        "An earlier send is unknown. Checking again did not send it.",
                        "早前的发送结果不明。再次核对没有发送。",
                      )
                    : failed
                      ? t(
                          "The check failed. That is not a confirmed new reply, and nothing was sent.",
                          "核对没有成功。这不是一次已确认的新回复，也没有发送。",
                        )
                      : t(
                          "The same reply is still on this task. Nothing was sent.",
                          "同一封回复仍在这件事务上。没有发送。",
                        ),
                }));
              },
            );
          }}
          onStartDraft={() => {
            setDrafting(reminder.id);
            setDraftText(LOCAL_REPLY_DRAFT);
          }}
          onDraftText={setDraftText}
          onReview={() => {
            const messageId = reminder.message_ids[reminder.message_ids.length - 1];
            void mutation.run(
              `/mail-followups/${reminder.id}/reply-drafts`,
              {
                message_id: messageId,
                fingerprint: reminder.fingerprint,
                observation_revision: reminder.observation_revision,
                summary: reminder.summary,
                body: draftText,
              },
              () => {
                setDrafting(null);
                changed();
              },
            );
          }}
          onDismiss={() => {
            void mutation.run(
              `/mail-followups/${reminder.id}/acknowledge`,
              { observed_revision: reminder.observation_revision },
              () => changed(),
            );
          }}
          onDecide={(action) => {
            if (!reminder.draft) return;
            void mutation.run<{ sent?: boolean }>(
              `/assistant/proposals/${reminder.draft.id}/decisions`,
              { action },
              (result) => {
                setNote((old) => ({
                  ...old,
                  [reminder.id]:
                    action === "cancel"
                      ? t("Draft discarded. Nothing was sent.", "草稿已放弃。没有发送。")
                      : result.sent
                        ? t(
                            "The result did not stay unsent. Check the task before trying again.",
                            "结果没有保持为未发送。请先查看事务。",
                          )
                        : "",
                }));
                changed();
              },
            );
          }}
        />
      ))}
      <MutationFeedback mutation={mutation} t={t} />
    </div>
  );
}

export function LocalMailSample({ t }: { t: Translate }) {
  const { data, offline, stale, refresh } = useWorkspace();
  const visible = data?.principal.kind === "owner" && !!data.personal_context_visible && !offline && !stale;
  const [threads, setThreads] = useState<{ id: string; subject: string; sender: string; followed: boolean }[]>([]);
  const [label, setLabel] = useState("");
  const mutation = usePrivateMutation();
  useEffect(() => {
    if (!visible) return;
    let live = true;
    const load = () => {
      void request<{ label: string; threads: { id: string; subject: string; sender: string; followed: boolean }[] }>(
        "/mail-followups/sample",
      ).then((reply) => {
        if (!live) return;
        setLabel(reply.label);
        setThreads(reply.threads);
      }).catch(() => {
        if (live) setThreads([]);
      });
    };
    load();
    window.addEventListener("desk:mail-reply", load);
    return () => {
      live = false;
      window.removeEventListener("desk:mail-reply", load);
    };
  }, [visible]);
  if (!visible) return null;
  const followed = threads.some((thread) => thread.followed);
  return (
    <section className="mail-reply-sample" aria-label={t("Local mail sample", "本地邮件样本")}>
      <h3>{t("Local mail sample", "本地邮件样本")}</h3>
      <p>{label || t("Local mail sample. Not a live mailbox.", "本地邮件样本。不是真实邮箱。")}</p>
      {threads.map((thread) => (
        <div className="workspace-inline-actions" key={thread.id}>
          <span>
            {thread.sender} · {thread.subject}
            {thread.followed ? t(" · Following", " · 跟进中") : ""}
          </span>
          {!thread.followed && (
            <button
              className="secondary"
              disabled={mutation.busy}
              onClick={() =>
                void mutation.run("/mail-followups/sample/follow", { thread_id: thread.id }, () => {
                  window.dispatchEvent(new Event("desk:mail-reply"));
                  void refresh();
                })
              }
            >
              {t("Follow", "跟进")}
            </button>
          )}
        </div>
      ))}
      <div className="workspace-inline-actions">
        <button
          className="secondary"
          disabled={mutation.busy || !followed}
          onClick={() =>
            void mutation.run("/mail-followups/sample/replies", {}, () => {
              window.dispatchEvent(new Event("desk:mail-reply"));
              void refresh();
            })
          }
        >
          {t("Simulate a reply", "模拟一封回复")}
        </button>
      </div>
      <MutationFeedback mutation={mutation} t={t} />
    </section>
  );
}
