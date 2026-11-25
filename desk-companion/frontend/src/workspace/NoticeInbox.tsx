import { useState } from "react";
import { Bell, Check, ChevronDown, Moon, Sunrise } from "lucide-react";
import { errorText } from "../api";
import type { Language, Translate } from "../types";
import type { DeskInbox } from "./useDeskInbox";
import type { DeskNotice } from "./notices";

export function NoticeInbox({
  inbox,
  language,
  zone,
  onReview,
  t,
}: {
  inbox: DeskInbox;
  language: Language;
  zone: string;
  onReview?: (
    page: "assistant" | "memory" | "tasks",
    noticeId?: string,
  ) => void;
  t: Translate;
}) {
  const [expanded, setExpanded] = useState<string[]>([]);
  if (!inbox.enabled) return null;
  const groups = new Map<string, DeskNotice[]>();
  for (const notice of inbox.notices) {
    const key =
      notice.kind === "morning_brief" || notice.kind === "evening_check"
        ? "kind/" + notice.kind
        : "notice/" + notice.id;
    const current = groups.get(key);
    if (current) current.push(notice);
    else groups.set(key, [notice]);
  }
  function dateOf(notice: DeskNotice) {
    if (!notice.created_at) return "";
    const date = new Date(notice.created_at);
    return Number.isNaN(date.getTime())
      ? ""
      : date.toLocaleString(language === "zh" ? "zh-HK" : "en-GB", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: zone,
        });
  }
  return (
    <section
      className="notice-inbox"
      aria-label={t("Alice updates", "Alice 动态")}
    >
      <div className="inbox-section-title">
        <h3>{t("Alice updates", "Alice 动态")}</h3>
        <span>{inbox.total}</span>
      </div>
      {Array.from(groups, ([key, items]) => {
        const [first] = items,
          open = expanded.includes(key);
        const Icon =
          first.kind === "morning_brief"
            ? Sunrise
            : first.kind === "evening_check"
              ? Moon
              : Bell;
        return (
          <article className="inbox-group" key={key}>
            <button
              className="inbox-group-toggle"
              type="button"
              aria-expanded={open}
              onClick={() =>
                setExpanded((old) =>
                  open ? old.filter((id) => id !== key) : [...old, key],
                )
              }
            >
              <span className="inbox-icon">
                <Icon size={17} />
              </span>
              <span>
                <strong>{t(first.title_en, first.title_zh)}</strong>
                <small>{dateOf(first)}</small>
              </span>
              {items.length > 1 && (
                <span className="inbox-count">{items.length}</span>
              )}
              <ChevronDown size={15} />
            </button>
            {open && (
              <ul>
                {items.map((item) => (
                  <li key={item.id}>
                    {items.length > 1 && <time>{dateOf(item)}</time>}
                    {onReview && item.kind === "initiative" ? (
                      <button
                        className="text-button"
                        onClick={() => onReview("assistant", item.id)}
                      >
                        {t("View in conversation", "在对话中查看")}
                      </button>
                    ) : (
                      <p>{t(item.body_en, item.body_zh)}</p>
                    )}
                    {onReview && item.kind === "memory_morning" && (
                      <button
                        className="text-button"
                        onClick={() => onReview("memory")}
                      >
                        {t("View memories", "查看记忆")}
                      </button>
                    )}
                    {onReview && item.kind === "followup" && (
                      <button
                        className="text-button"
                        onClick={() => onReview("tasks")}
                      >
                        {t("View tasks", "查看待办")}
                      </button>
                    )}
                    {t(item.reason_en, item.reason_zh) && (
                      <small>{t(item.reason_en, item.reason_zh)}</small>
                    )}
                    <button
                      className="text-button"
                      type="button"
                      disabled={inbox.busy}
                      onClick={() => void inbox.dismiss(item.id)}
                    >
                      <Check size={15} />
                      {t("Dismiss", "知道了")}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </article>
        );
      })}
      {inbox.loaded && inbox.total === 0 && !inbox.error && (
        <p className="inbox-empty">{t("No new updates.", "暂无新动态。")}</p>
      )}
      {inbox.next && (
        <button
          className="text-button"
          disabled={inbox.busy}
          onClick={() => void inbox.more()}
        >
          {t("Show earlier updates", "查看更早动态")}
        </button>
      )}
      {!!inbox.error && (
        <div role="alert" className="error-message">
          {errorText(inbox.error, t)}{" "}
          <button className="text-button" onClick={() => void inbox.refresh()}>
            {t("Retry", "重试")}
          </button>
        </div>
      )}
    </section>
  );
}