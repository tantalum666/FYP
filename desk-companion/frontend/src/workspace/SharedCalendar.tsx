import { useEffect, useState } from "react";
import { request } from "../api";
import { DateTime } from "luxon";
interface Shared {
  mode: string;
  start: string;
  end: string;
  timezone: string;
  expires_at: string;
  items: Array<{
    start: string;
    end: string;
    title?: string;
    all_day?: boolean;
  }>;
}
export function SharedCalendar() {
  const [data, setData] = useState<Shared | null>(null),
    [failed, setFailed] = useState(false),
    [language, setLanguage] = useState("en");
  useEffect(() => {
    let alive = true;
    const token = location.hash.slice(1);
    const load = async () => {
      try {
        const next = await request<Shared>("/share/view", {
          headers: { "X-Desk-Share": token },
        });
        if (alive) {
          setData(next);
          setFailed(false);
        }
      } catch {
        if (alive) {
          setData(null);
          setFailed(true);
        }
      }
    };
    void load();
    const timer = setInterval(() => void load(), 30000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  const t = (en: string, zh: string) => (language === "zh" ? zh : en);
  return (
    <main className="shared-page">
      <header>
        <span>Desk Companion</span>
        <select
          aria-label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </header>
      <h1>{t("Shared calendar", "共享日历")}</h1>
      {failed ? (
        <p role="alert">
          {t(
            "This link is unavailable, expired or revoked.",
            "此链接不可用、已过期或已撤销。",
          )}
        </p>
      ) : data ? (
        <>
          <p>
            {data.start} → {data.end} · {data.timezone}
          </p>
          <p>
            {data.mode === "busy"
              ? t(
                  "Busy times only. Titles and private details are hidden.",
                  "仅显示忙闲时间，标题与私人详情已隐藏。",
                )
              : t(
                  "Only events marked displayable are included.",
                  "仅包含标为可展示的事项。",
                )}
          </p>
          <div className="shared-events">
            {data.items.map((item, i) => (
              <article key={i}>
                <strong>{item.title ?? t("Busy", "忙碌")}</strong>
                <p>
                  {DateTime.fromISO(item.start)
                    .setZone(data.timezone)
                    .toFormat("dd LLL yyyy HH:mm")}{" "}
                  →{" "}
                  {DateTime.fromISO(item.end)
                    .setZone(data.timezone)
                    .toFormat("dd LLL HH:mm")}
                </p>
              </article>
            ))}
          </div>
          {!data.items.length && (
            <p>
              {t("No shared events in this range.", "此范围内没有共享事项。")}
            </p>
          )}
          <small>
            {t("Read-only · expires ", "只读 · 有效至 ")}
            {DateTime.fromISO(data.expires_at)
              .setZone(data.timezone)
              .toFormat("dd LLL yyyy HH:mm")}
          </small>
        </>
      ) : (
        <p>{t("Loading…", "正在读取…")}</p>
      )}
    </main>
  );
}
