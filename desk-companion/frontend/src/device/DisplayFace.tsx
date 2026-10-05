import { DateTime } from "luxon";
import {
  Bell,
  ListTodo,
  CameraOff,
  Hand,
  LockKeyhole,
  RefreshCw,
  WifiOff,
} from "lucide-react";
import { eventTime, inZone, locale, occursOn, title } from "../dates";
import type { Language, Occurrence, Snapshot, Translate } from "../types";
import { calendarDays, upcomingEvents } from "./model";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { feedbackText, postureLabel } from "../workspace/PosturePanel";
import { Avatar } from "../workspace/Avatar";
import { lunarDate } from "../workspace/calendarExtras";

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
  onPosture: () => void;
  onTasks: () => void;
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
  onPosture,
  onTasks,
  t,
}: Props) {
  const workspace = useWorkspace();
  const posture = workspace.data?.posture;
  const extras = workspace.data?.calendar_extras;
  const feedback =
    posture?.feedback && now.toSeconds() - posture.feedback.created_at < 180
      ? posture.feedback
      : posture?.movement_feedback;
  const showPostureFeedback =
    !!feedback &&
    posture?.connected &&
    !posture.paused &&
    posture.preferences.enabled &&
    !workspace.offline &&
    now.toSeconds() - feedback.created_at < 180 &&
    now.toSeconds() >= (posture?.snooze_until ?? 0);
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
          {extras?.preferences.show_lunar && (
            <small className="display-lunar">{lunarDate(now, language)}</small>
          )}
          {extras?.holidays[language][now.toISODate()!] && (
            <small className="display-holiday">
              {extras.holidays[language][now.toISODate()!]}
            </small>
          )}
          {extras?.weather.temperature_c !== undefined && (
            <small className="display-weather">
              {extras.weather.temperature_c}°C · {t("Hong Kong", "香港")}
              {extras.weather.status === "stale"
                ? t(" · Last reading", " · 上次观测")
                : ""}
            </small>
          )}
        </div>
      </header>
      <div className="display-content">
        {extras?.preferences.avatar_display === "companion" ? (
          <Avatar language={language} />
        ) : (
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
                    aria-label={`${t("Open ", "打开 ")}${day.toISODate()}${hasEvents ? t(", has events", "，有日程") : ""} ${extras?.holidays[language][day.toISODate()!] ?? ""}`}
                    aria-current={isToday ? "date" : undefined}
                    onClick={() => onDay(day)}
                  >
                    <span
                      className={`display-day-number ${extras?.holidays[language][day.toISODate()!] ? "public-holiday" : ""}`}
                    >
                      {day.day}
                    </span>
                    <span
                      className={`display-event-dot ${hasEvents ? "marked" : ""}`}
                    />
                  </button>
                );
              })}
            </div>
          </section>
        )}
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
      {showPostureFeedback && feedback ? (
        <button className="display-alert" onClick={onPosture}>
          <Bell />
          <span>
            <strong>
              {feedback.outcome === "adjusted"
                ? t("Position adjusted", "已调整位置")
                : feedback.outcome === "unknown"
                  ? t("Unable to reassess", "无法完成复测")
                  : t("A small adjustment", "调整一下位置")}
              {posture?.source === "replay" ? t(" · Replay", " · 回放") : ""}
            </strong>
            <span>
              {feedback.outcome === "adjusted"
                ? t("Back within your personal reference", "已回到个人参考范围")
                : feedbackText(feedback.kind, t)}
            </span>
          </span>
          <span>{t("Open", "查看")}</span>
        </button>
      ) : (
        due.length > 0 && (
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
        )
      )}
      <footer className="display-footer">
        {state === "ready" &&
          !workspace.stale &&
          !workspace.offline &&
          !!workspace.data?.tasks?.active_count && (
            <button className="display-task-link" onClick={onTasks}>
              <ListTodo size={18} />
              <span>
                {workspace.data.tasks.due_count
                  ? t(
                      `${workspace.data.tasks.due_count} check-in ready`,
                      `${workspace.data.tasks.due_count}项待更新进展`,
                    )
                  : t(
                      `${workspace.data.tasks.active_count} active tasks`,
                      `${workspace.data.tasks.active_count}项事务`,
                    )}
              </span>
            </button>
          )}
        <div className="display-status">
          <CameraOff />
          <div>
            <span>
              {workspace.offline
                ? t("Desk connection lost", "桌面连接中断")
                : postureLabel(workspace.data?.posture, t)}
            </span>
            {workspace.data?.posture.source === "replay" && (
              <small>{t("Replay posture input", "坐姿回放输入")}</small>
            )}
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
