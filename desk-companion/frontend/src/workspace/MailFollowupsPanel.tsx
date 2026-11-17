import { useEffect, useRef, useState } from "react";
import { ApiError, request, errorText } from "../api";
import type { Translate } from "../types";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import "./mail-followups.css";

interface MailFollowup {
  id: string;
  task_id: string;
  state: string;
  paused_by_preferences?: boolean;
  subject: string;
  sender: string;
  account_email: string;
  unread_count: number;
  observation_revision: number;
  last_checked_at: string | null;
  expires_at: string;
  error: string | null;
  latest_messages: {
    id: string;
    subject: string;
    sender: string;
    at: string;
    outgoing: boolean;
  }[];
}

export function MailFollowupsPanel({
  t,
  visible,
  fresh,
  blocked = false,
  refreshToken,
  taskId,
  onOpenTask,
  onDiscuss,
}: {
  t: Translate;
  visible: boolean;
  fresh: boolean;
  blocked?: boolean;
  refreshToken?: number;
  taskId?: string;
  onOpenTask?: (id: string) => void;
  onDiscuss?: () => void;
}) {
  const [data, setData] = useState<{
    scope: string;
    rows: MailFollowup[];
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [reload, setReload] = useState(0);
  const [identity, setIdentity] = useState(0);
  const mutation = usePrivateMutation();
  const clear = useRef(mutation.clear);
  clear.current = mutation.clear;
  const scope = `${taskId ?? "all"}/${identity}`;
  useEffect(() => {
    const reset = () => {
      setIdentity((value) => value + 1);
      setData(null);
      clear.current();
    };
    window.addEventListener("desk:session", reset);
    return () => window.removeEventListener("desk:session", reset);
  }, []);
  useEffect(() => {
    if (!visible) {
      setData(null);
      setError(null);
      clear.current();
      return;
    }
    if (!fresh) return;
    let live = true;
    void request<{ followups: MailFollowup[] }>(
      `/mail-followups${taskId ? `?task_id=${taskId}` : ""}`,
    )
      .then((reply) => {
        if (live) {
          setData({ scope, rows: reply.followups });
          setError(null);
        }
      })
      .catch((failure) => {
        if (live) {
          setData(null);
          setError(failure);
        }
      });
    return () => {
      live = false;
    };
  }, [visible, fresh, taskId, scope, refreshToken, reload]);
  const rows = visible && fresh && data?.scope === scope ? data.rows : [];
  const epoch = useRef(scope);
  epoch.current = visible ? scope : "hidden";
  const busy = mutation.busy || mutation.pending || blocked;
  async function act(row: MailFollowup, action: "stop" | "acknowledge") {
    const started = scope;
    await mutation.run(
      `/mail-followups/${row.id}/${action}`,
      action === "acknowledge"
        ? { observed_revision: row.observation_revision }
        : {},
      () => {
        if (epoch.current === started) setReload((value) => value + 1);
      },
    );
  }
  if (!visible || !fresh) return null;
  if (error)
    return (
      <p role="status" className="mail-followup-error">
        {errorText(error, t)}{" "}
        <button
          className="text-button"
          onClick={() => setReload((value) => value + 1)}
        >
          {t("Refresh", "刷新")}
        </button>
      </p>
    );
  if (!rows.length && !mutation.pending && !mutation.error) return null;
  const unread = rows.reduce((sum, row) => sum + row.unread_count, 0);
  return (
    <details
      className="mail-followups"
      open={mutation.pending || !!mutation.error || (!!taskId && unread > 0)}
    >
      <summary>
        {t("Followed emails", "邮件跟进")}
        {unread > 0 ? ` · ${t(`${unread} new`, `${unread} 条更新`)}` : ""}
      </summary>
      {rows.map((row) => (
        <article key={row.id} className="mail-followup-item">
          <strong>{row.subject || t("No subject", "无主题")}</strong>
          <small>{row.account_email}</small>
          <p>
            {row.paused_by_preferences
              ? t("Checks paused in your preferences", "已按偏好暂停检查")
              : row.state === "active"
                ? row.unread_count
                  ? t(
                      `${row.unread_count} new message(s) to review`,
                      `${row.unread_count} 条新消息待查看`,
                    )
                  : t("Following this thread", "正在跟进这段邮件对话")
                : row.state === "blocked"
                  ? t("Connection needs attention", "连接需要处理")
                  : t("Follow-up ended", "跟进已结束")}
          </p>
          {row.last_checked_at && (
            <small>
              {t("Last checked: ", "上次检查：")}
              {new Date(row.last_checked_at).toLocaleString(
                t("en-HK", "zh-CN"),
              )}
            </small>
          )}
          {row.error && (
            <p role="status">{errorText(new ApiError(row.error), t)}</p>
          )}
          {!!taskId && row.latest_messages.length > 0 && (
            <ul className="mail-followup-messages">
              {row.latest_messages.map((message) => (
                <li key={message.id}>
                  <span>
                    {message.outgoing ? t("You", "你") : message.sender}
                  </span>
                  <small>
                    {new Date(message.at).toLocaleString(t("en-HK", "zh-CN"))}
                  </small>
                  <span>{message.subject || t("No subject", "无主题")}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="workspace-inline-actions">
            {onOpenTask && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() => onOpenTask(row.task_id)}
              >
                {t("Open task", "打开事务")}
              </button>
            )}
            {onDiscuss && (
              <button
                className="text-button"
                disabled={busy}
                onClick={onDiscuss}
              >
                {t("Ask Alice about this update", "和 Alice 看看这条更新")}
              </button>
            )}
            {row.unread_count > 0 && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => void act(row, "acknowledge")}
              >
                {t("Mark reviewed", "已查看")}
              </button>
            )}
            {["active", "blocked"].includes(row.state) && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void act(row, "stop")}
              >
                {t("Stop following", "停止跟进")}
              </button>
            )}
          </div>
        </article>
      ))}
      <MutationFeedback mutation={mutation} t={t} />
    </details>
  );
}
