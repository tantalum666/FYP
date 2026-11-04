import type { Translate } from "../types";
import type { Proposal } from "./assistantTypes";

export function JourneyAdvice({
  proposal,
  t,
}: {
  proposal: Proposal;
  t: Translate;
}) {
  const { kind, data } = proposal;
  const changes = data.shopping?.provided_fields;
  const source = data.mail_id ?? data.event_uid ?? data.shopping?.event_id;
  const observed = data.observed_at ?? data.shopping?.observed_at;
  return (
    <>
      <h3>
        {kind === "mailbox_reply"
          ? t("Review email advice", "核对邮件建议")
          : kind === "shopping_advice"
            ? t("Review shopping update", "核对购物进展")
            : t("Review calendar advice", "核对日程建议")}
      </h3>
      {data.title && (
        <p>
          <strong>{data.title}</strong>
        </p>
      )}
      {data.reply_draft && (
        <details>
          <summary>{t("Reply draft", "回复草稿")}</summary>
          <blockquote>{data.reply_draft}</blockquote>
        </details>
      )}
      {changes?.title && (
        <p>
          {t("Task: ", "事务：")}
          {changes.title}
        </p>
      )}
      {changes?.status && (
        <p>
          {t("Status: ", "状态：")}
          {changes.status === "waiting"
            ? t("Waiting", "等待中")
            : changes.status === "in_progress"
              ? t("In progress", "进行中")
              : t("To do", "待处理")}
        </p>
      )}
      {changes?.waiting_for && (
        <p>
          {t("Waiting for: ", "等待：")}
          {changes.waiting_for}
        </p>
      )}
      {changes?.next_step && (
        <p>
          {t("Next: ", "下一步：")}
          {changes.next_step}
        </p>
      )}
      <details>
        <summary>{t("Source and details", "来源与详情")}</summary>
        <p>{data.summary ?? data.shopping?.note}</p>
        <small>
          {t("Source: ", "来源：")}
          {source}
          {observed ? ` · ${observed}` : ""}
        </small>
      </details>
      <p>
        {kind === "mailbox_reply"
          ? t(
              "Confirmation saves a review note; it does not send the email.",
              "确认后保存核对记录，不会发送邮件。",
            )
          : kind === "shopping_advice"
            ? t(
                "Confirmation saves this task update; it does not place an order or pay.",
                "确认后保存事务进展，不会下单或付款。",
              )
            : t(
                "Confirmation saves a review note; it does not accept the invitation or send an RSVP.",
                "确认后保存核对记录，不会接受邀请或发送回复。",
              )}
      </p>
    </>
  );
}
