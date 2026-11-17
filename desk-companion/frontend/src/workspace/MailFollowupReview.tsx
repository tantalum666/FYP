import { useState } from "react";
import type { Translate } from "../types";
import type { Proposal, ProposalDecisionOptions } from "./assistantTypes";
import "./mail-followups.css";

export function MailFollowupReview({
  proposal,
  t,
  busy,
  onDecision,
}: {
  proposal: Proposal;
  t: Translate;
  busy: boolean;
  onDecision: (
    action: "confirm" | "cancel",
    options?: ProposalDecisionOptions,
  ) => void;
}) {
  const [allowed, setAllowed] = useState(false);
  const mail = proposal.data.mail_followup;
  if (!mail) return null;
  return (
    <article className="assistant-action-card mail-followup-review">
      <span className="workspace-eyebrow">
        {t("Follow this email", "跟进这封邮件")}
      </span>
      <h3>{mail.selected.subject || t("No subject", "无主题")}</h3>
      <p>{mail.selected.sender}</p>
      <small>
        {new Date(mail.selected.at).toLocaleString(t("en-HK", "zh-CN"))} ·{" "}
        {mail.provider === "gmail" ? "Gmail" : "Outlook"} · {mail.account_email}
      </small>
      <p>
        {t(
          `Check every ${mail.interval_minutes} minutes for ${mail.duration_days} days.`,
          `每 ${mail.interval_minutes} 分钟检查一次，持续 ${mail.duration_days} 天。`,
        )}
      </p>
      <details>
        <summary>{t("What will be kept", "查看跟进范围")}</summary>
        <p>
          {t(
            "Read sender, subject and time for this thread. Keep the linked task and update history on this desk.",
            "读取这段邮件对话的发件人、标题和时间，在本机保留关联事务与更新记录。",
          )}
        </p>
        <p>
          {t("Task: ", "关联事务：")}
          {mail.task_title}
        </p>
        <p>
          {t(
            "You can stop at any time. Replies need your separate review.",
            "你可以随时停止。回复邮件仍需另行确认。",
          )}
        </p>
      </details>
      <label className="mail-followup-consent">
        <input
          type="checkbox"
          checked={allowed}
          disabled={busy}
          onChange={(event) => setAllowed(event.target.checked)}
        />
        {t(
          "Allow background follow-up of this email thread",
          "允许在后台跟进这段邮件对话",
        )}
      </label>
      <div className="workspace-inline-actions">
        <button
          className="primary"
          disabled={busy || !allowed}
          onClick={() => onDecision("confirm", { follow_mail_thread: true })}
        >
          {t("Start following", "开始跟进")}
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => onDecision("cancel")}
        >
          {t("Cancel", "取消")}
        </button>
      </div>
    </article>
  );
}
