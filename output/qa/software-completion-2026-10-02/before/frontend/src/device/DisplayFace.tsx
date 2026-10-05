import { DateTime } from "luxon";
import {
  Bell,
  CameraOff,
  Hand,
  LockKeyhole,
  RefreshCw,
  WifiOff,
} from "lucide-react";
import { eventTime, inZone, locale, occursOn, title } from "../dates";
import type { Language, Occurrence, Snapshot, Translate } from "../types";
import { calendarDays, upcomingEvents } from "./model";

interface Props {
  now: DateTime;
  data: Snapshot | null;
  language: Language;
  state: "loading" | "ready" | "offline" | "locked";
  pending: boolean;
  onManage: () => void;
  onEvent: (event: Occurrence) => void;
  onDay: (day: DateTime) => void;
  onReminders: () => void;
  onRetry: () => void;
  t: Translate;
}

function relativeTime(
  event: Occurrence,
  now: DateTime,
  language: Language,
  t: Translate,
) {
  const start = inZone(event.start, now.zoneName!);
  const day =
    start.toISODate() === now.toISODate()
      ? t("Today", "今天")
      : start.toISODate() === now.plus({ days: 1 }).toISODate()
        ? t("Tomorrow", "明天")
        : start
            .setLocale(locale(language))
            .toFormat(start < now.plus({ days: 7 }) ? "cccc" : "d LLL");
  return (
    day +
    " · " +
    (event.all_day ? t("All day", "全天") : start.toFormat("HH:mm"))
  );
}

export function DisplayFace({
  now,
  data,
  language,
  state,
  pending,
  onManage,
  onEvent,
  onDay,
  onReminders,
  onRetry,
  t,
}: Props) {
  const days = calendarDays(now);
  const events = data?.occurrences ?? [];
  const upcoming = upcomingEvents(events, now);
  const lead = upcoming[0];
  const due = data?.reminders.filter((r) => r.status === "due") ?? [];
  const unavailable =
    state === "locked"
      ? t("Calendar locked", "日历已锁定")
      : state === "loading"
        ? t("Connecting calendar…", "正在连接日历…")
        : t("Calendar unavailable", "暂时无法读取日历");
  return (
    <main
      className="display-face"
      aria-label={t("Desk display", "桌面常亮显示")}
    >
      <header className="display-header">
        <time
          className="display-clock"
          dateTime={now.toISO()!}
          aria-label={t("Current time ", "当前时间 ") + now.toFormat("HH:mm")}
        >
          {now.toFormat("HH:mm")}
        </time>
        <div className="display-date">
          <div>{now.setLocale(locale(language)).toFormat("cccc")}</div>
          <p>
            {now
              .setLocale(locale(language))
              .toFormat(language === "en" ? "d LLLL yyyy" : "yyyy年M月d日")}
          </p>
        </div>
      </header>
      <div className="display-content">
        <section
          className="display-month"
          aria-label={t("Current month", "本月日期")}
        >
          <h1>
            {now
              .setLocale(locale(language))
              .toFormat(language === "en" ? "LLLL" : "M月")}{" "}
            <span>{now.year}</span>
          </h1>
          <div className="display-weekdays" aria-hidden="true">
            {days.slice(0, 7).map((d) => (
              <span key={d.weekday}>
                {language === "en"
                  ? d.toFormat("ccccc")
                  : ["一", "二", "三", "四", "五", "六", "日"][d.weekday - 1]}
              </span>
            ))}
          </div>
          <div
            className={`display-month-grid rows-${days.length / 7}`}
            style={{
              gridTemplateRows: `repeat(${days.length / 7}, minmax(0,1fr))`,
            }}
          >
            {days.map((day) => {
              const hasEvents = events.some((e) =>
                occursOn(e, day, now.zoneName!),
              );
              const isToday = day.toISODate() === now.toISODate();
              return (
                <button
                  key={day.toISODate()}
                  className={`${day.month !== now.month ? "month-outside" : ""} ${isToday ? "current-date" : ""}`}
                  aria-label={`${t("Open ", "打开 ")}${day.toISODate()}${hasEvents ? t(", has events", "，有日程") : ""}`}
                  aria-current={isToday ? "date" : undefined}
                  onClick={() => onDay(day)}
                >
                  <span className="display-day-number">{day.day}</span>
                  <span
                    className={`display-event-dot ${hasEvents ? "marked" : ""}`}
                  />
                </button>
              );
            })}
          </div>
        </section>
        <section
          className="display-agenda"
          aria-label={t("Upcoming schedule", "近期安排")}
        >
          {data ? (
            lead ? (
              <>
                <button className="display-lead" onClick={() => onEvent(lead)}>
                  <span className="display-section-label">
                    {lead.all_day &&
                    occursOn(lead, now.startOf("day"), now.zoneName!)
                      ? t("Today", "今天")
                      : inZone(lead.start, now.zoneName!) <= now
                        ? t("Now", "现在")
                        : t("Up next", "接下来")}
                  </span>
                  <strong>{title(lead, language)}</strong>
                  <span className="display-lead-time">
                    {eventTime(lead, now.zoneName!, language)}
                  </span>
                  {!occursOn(lead, now.startOf("day"), now.zoneName!) && (
                    <span className="display-future-date">
                      {relativeTime(lead, now, language, t)}
                    </span>
                  )}
                </button>
                {upcoming.slice(1, 3).map((event) => (
                  <button
                    className="display-later"
                    key={event.id + event.occurrence_key}
                    onClick={() => onEvent(event)}
                  >
                    <span>{relativeTime(event, now, language, t)}</span>
                    <strong>{title(event, language)}</strong>
                  </button>
                ))}
              </>
            ) : (
              <div className="display-empty">
                <span className="display-section-label">
                  {t("Up next", "接下来")}
                </span>
                <h2>{t("Nothing scheduled.", "暂时没有安排。")}</h2>
                <p>
                  {t(
                    "Touch to plan your next day.",
                    "轻触屏幕，安排接下来的一天。",
                  )}
                </p>
              </div>
            )
          ) : (
            <div className="display-empty">
              <span className="display-section-label">
                {t("Your calendar", "你的日历")}
              </span>
              <h2>{unavailable}</h2>
              <button onClick={state === "locked" ? onManage : onRetry}>
                {state === "locked" ? <LockKeyhole /> : <RefreshCw />}
                {state === "locked"
                  ? t("Sign in", "登录")
                  : t("Reconnect", "重新连接")}
              </button>
            </div>
          )}
        </section>
      </div>
      {due.length > 0 && (
        <button className="display-alert" onClick={onReminders}>
          <Bell />
          <span>
            <strong>{t("Reminder due", "有待处理提醒")}</strong>
            <span>
              {title(due[0], language)}
              {due.length > 1 ? ` · +${due.length - 1}` : ""}
            </span>
          </span>
          <span>{t("Open", "查看")}</span>
        </button>
      )}
      <footer className="display-footer">
        <div className="display-status">
          <CameraOff />
          <div>
            <span>{t("Camera not connected", "摄像头未连接")}</span>
            {data?.has_samples && (
              <small>{t("Example calendar", "含示例日程")}</small>
            )}
            {state === "offline" && (
              <button onClick={onRetry}>
                <WifiOff size={16} />
                {t("Offline", "已离线")}
                {data &&
                  ` · ${inZone(data.server_time, now.zoneName!).toFormat("HH:mm")}`}
              </button>
            )}
          </div>
        </div>
        <button className="display-manage" onClick={onManage}>
          <Hand />
          <span>
            {pending
              ? t("Save needs confirmation", "有待确认的保存")
              : t("Touch to manage", "轻触以操作")}
          </span>
        </button>
      </footer>
    </main>
  );
}
