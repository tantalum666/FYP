import { DateTime } from "luxon";
import {
  ArrowUpRight,
  CalendarDays,
  Check,
  ChevronRight,
  ListTodo,
  Monitor,
  Plus,
} from "lucide-react";
import { eventTime, inZone, locale, title } from "../dates";
import { privateDisplayHidden } from "../device/privacy";
import type { Language, Occurrence, Snapshot, Translate } from "../types";
import { lunarDate } from "../workspace/calendarExtras";
import { MomentCard } from "../workspace/MomentCard";
import { feedbackText, postureLabel } from "../workspace/PosturePanel";
import { useWorkspace } from "../workspace/WorkspaceContext";

export function TodayView({
  snapshot,
  language,
  now,
  onNew,
  onOpen,
  onCalendar,
  onDevice,
  onTasks,
  t,
}: {
  snapshot: Snapshot;
  language: Language;
  now: DateTime;
  onNew: () => void;
  onOpen: (event: Occurrence) => void;
  onCalendar: () => void;
  onDevice: () => void;
  onTasks: (id?: string) => void;
  t: Translate;
}) {
  const { data, offline, stale } = useWorkspace();
  const zone = snapshot.settings.timezone;
  const local = now.setZone(zone).setLocale(locale(language));
  const calendar = data?.calendar_extras;
  const fresh = !!data && !offline && !stale;
  const visible =
    fresh &&
    data.personal_context_visible &&
    !privateDisplayHidden(data.posture, stale);
  const tasks = visible
    ? (data.tasks.preview ?? data.tasks.attention)
        .filter(
          (task) =>
            !task.redacted && !["completed", "cancelled"].includes(task.status),
        )
        .slice(0, 4)
    : [];
  const upcoming = snapshot.occurrences.find(
    (event) =>
      !event.completed && !event.all_day && inZone(event.end, zone) > now,
  );
  const feedback =
    fresh &&
    data.posture.feedback &&
    now.toSeconds() - data.posture.feedback.created_at < 180
      ? data.posture.feedback
      : null;
  return (
    <div className="today-view workspace-page">
      <header className="page-heading">
        <div>
          <h1>{t("Today", "今天")}</h1>
          <p>
            {local.toFormat(language === "en" ? "cccc, d LLLL" : "M月d日 cccc")}{" "}
            · {zone.replaceAll("_", " ").split("/").at(-1)}
            {calendar?.weather.temperature_c != null && (
              <>
                {" "}
                · {calendar.weather.temperature_c}°C {t("Hong Kong", "香港")}
                {calendar.weather.status === "stale" &&
                  t(" (last reading)", "（上次观测）")}
              </>
            )}
            {calendar?.preferences.show_lunar && (
              <> · {lunarDate(local, language)}</>
            )}
            {calendar?.holidays[language][local.toISODate()!] && (
              <> · {calendar.holidays[language][local.toISODate()!]}</>
            )}
          </p>
        </div>
        <button className="primary" onClick={onNew}>
          <Plus size={17} />
          {t("New event", "新建日程")}
        </button>
      </header>
      <div className="today-layout">
        <div className="today-main">
          <section className="daily-agenda">
            <div className="section-title-row">
              <h2>{t("Today’s agenda", "今日安排")}</h2>
              <button className="text-button" onClick={onCalendar}>
                {t("Calendar", "日历")}
                <ArrowUpRight size={15} />
              </button>
            </div>
            {snapshot.has_samples && (
              <small className="sample-note">
                {t("Example calendar", "含示例日程")}
              </small>
            )}
            {snapshot.occurrences.length ? (
              snapshot.occurrences.map((e) => (
                <button
                  key={e.id + e.occurrence_key}
                  onClick={() => onOpen(e)}
                  className={`daily-event ${e.completed ? "completed" : e === upcoming ? "next-up" : ""}`}
                >
                  <time>
                    {e.all_day
                      ? t("All day", "全天")
                      : inZone(e.start, zone).toFormat("HH:mm")}
                  </time>
                  <i className={e.color} />
                  <span>
                    <strong>{title(e, language)}</strong>
                    <small>
                      {eventTime(e, zone, language)}
                      {e.location && " · " + e.location}
                    </small>
                  </span>
                  {e.completed ? (
                    <Check size={16} />
                  ) : e === upcoming ? (
                    <small className="up-next-label">
                      {t("Up next", "接下来")}
                    </small>
                  ) : (
                    <ChevronRight size={15} />
                  )}
                </button>
              ))
            ) : (
              <div className="calendar-empty">
                <CalendarDays />
                <p>{t("No events today.", "今天没有日程。")}</p>
              </div>
            )}
          </section>
        </div>
        <aside className="today-aside">
          <section className="daily-tasks">
            <div className="section-title-row">
              <h2>{t("Tasks", "待办")}</h2>
              {fresh && (
                <span className="section-count">{data.tasks.active_count}</span>
              )}
            </div>
            {tasks.map((task) => (
              <button
                key={task.id}
                className="daily-task"
                onClick={() => onTasks(task.id)}
              >
                <span className="task-indicator" />
                <span>
                  <strong>{task.title}</strong>
                  {task.next_step && <small>{task.next_step}</small>}
                </span>
                <ChevronRight size={15} />
              </button>
            ))}
            {!tasks.length && (
              <p className="quiet-state">
                {fresh && !data.tasks.active_count
                  ? t("No active tasks.", "暂无待办。")
                  : t("Open tasks to see your list.", "打开待办查看清单。")}
              </p>
            )}
            <button className="text-button" onClick={() => onTasks()}>
              <ListTodo size={16} />
              {t("View tasks", "查看待办")}
              <ChevronRight size={14} />
            </button>
          </section>
          <MomentCard t={t} />
          <button className="today-status" onClick={onDevice}>
            <Monitor size={18} />
            <span>
              <strong>{t("Desk status", "桌面状态")}</strong>
              <small>
                {offline
                  ? t("Desk connection lost", "桌面连接中断")
                  : postureLabel(data?.posture, t)}
              </small>
            </span>
            <ChevronRight size={15} />
          </button>
          {feedback && (
            <button className="today-status" onClick={onDevice}>
              <span>
                <strong>{feedbackText(feedback.kind, t)}</strong>
                <small>
                  {data?.posture.source === "replay"
                    ? t("Replay feedback", "回放反馈")
                    : t("Posture feedback", "坐姿反馈")}
                </small>
              </span>
              <ChevronRight size={15} />
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}
