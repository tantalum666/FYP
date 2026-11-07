import { DateTime } from "luxon";
import { CalendarDays, ChevronRight, ListTodo } from "lucide-react";
import type { Language, Occurrence, Translate } from "../types";
import { privateDisplayHidden } from "../device/privacy";
import { title } from "../dates";
import { useWorkspace } from "../workspace/WorkspaceContext";

/** Presentation only: reuse the parent's calendar and existing workspace task read. */
export function AliceAgenda({
  events,
  now,
  zone,
  language,
  t,
  obscured,
  onCalendar,
  onEvent,
  onTasks,
  monthPreview = false,
}: {
  monthPreview?: boolean;
  events: Occurrence[] | null;
  now: DateTime;
  zone: string;
  language: Language;
  t: Translate;
  obscured: boolean;
  onCalendar: () => void;
  onEvent: (event: Occurrence) => void;
  onTasks: () => void;
}) {
  const { data, offline, stale } = useWorkspace();
  const privateVisible =
    data?.personal_context_visible &&
    !offline &&
    !stale &&
    !privateDisplayHidden(data.posture, stale);
  const upcoming = privateVisible
    ? (events
        ?.filter((e) => !e.completed && DateTime.fromISO(e.end) > now)
        .slice(0, 2) ?? [])
    : [];
  const tasks = privateVisible
    ? (data.tasks.preview ?? data.tasks.attention)
        .filter(
          (task) =>
            !task.redacted && !["completed", "cancelled"].includes(task.status),
        )
        .slice(0, 2)
    : [];
  const today = now.setZone(zone);
  return (
    <aside
      className="alice-agenda"
      inert={obscured}
      aria-hidden={obscured}
      aria-label={t("Your day", "你的一天")}
    >
      <section className="alice-agenda-calendar">
        <button className="alice-agenda-heading" onClick={onCalendar}>
          <CalendarDays size={16} />
          <span>
            {monthPreview
              ? today
                  .setLocale(language === "zh" ? "zh-CN" : "en-GB")
                  .toFormat(language === "zh" ? "M月" : "MMMM")
              : t("Today", "今天")}
          </span>
          <small>
            {today
              .setLocale(language === "zh" ? "zh-CN" : "en-GB")
              .toFormat(language === "zh" ? "M月d日" : "d MMM")}
          </small>
          <ChevronRight size={14} />
        </button>
        {monthPreview ? (
          <button
            className="alice-month-preview"
            onClick={onCalendar}
            aria-label={t("Open full calendar", "打开完整日历")}
          >
            <span className="alice-month-weekdays" aria-hidden="true">
              {Array.from({ length: 7 }, (_, i) => (
                <small key={i}>
                  {today
                    .startOf("week")
                    .plus({ days: i })
                    .setLocale(language === "zh" ? "zh-CN" : "en-GB")
                    .toFormat(language === "zh" ? "ccccc" : "ccc")}
                </small>
              ))}
            </span>
            <span className="alice-month-dates" aria-hidden="true">
              {Array.from(
                {
                  length:
                    Math.ceil(
                      (today.startOf("month").weekday -
                        1 +
                        today.daysInMonth!) /
                        7,
                    ) * 7,
                },
                (_, i) => {
                  const day = today
                    .startOf("month")
                    .startOf("week")
                    .plus({ days: i });
                  return (
                    <span
                      key={i}
                      className={`${day.month !== today.month ? "outside" : ""} ${day.hasSame(today, "day") ? "current" : ""}`}
                    >
                      {day.day}
                    </span>
                  );
                },
              )}
            </span>
          </button>
        ) : (
          <div className="alice-week" aria-hidden="true">
            {Array.from({ length: 7 }, (_, i) => {
              const day = today.startOf("week").plus({ days: i });
              return (
                <span
                  key={i}
                  className={day.hasSame(today, "day") ? "current" : ""}
                >
                  <small>
                    {day
                      .setLocale(language === "zh" ? "zh-CN" : "en-GB")
                      .toFormat("ccc")}
                  </small>
                  <b>{day.day}</b>
                </span>
              );
            })}
          </div>
        )}
        <div className="alice-agenda-rows">
          {upcoming.length ? (
            upcoming.map((event) => (
              <button
                key={`${event.id}/${event.occurrence_key}`}
                onClick={() => onEvent(event)}
              >
                <time>
                  {event.all_day
                    ? t("All day", "全天")
                    : DateTime.fromISO(event.start)
                        .setZone(zone)
                        .toFormat("HH:mm")}
                </time>
                <span>{title(event, language)}</span>
              </button>
            ))
          ) : (
            <button onClick={onCalendar}>
              <span>
                {events === null || !privateVisible
                  ? t("View calendar", "查看日历")
                  : t("No upcoming events", "暂无日程")}
              </span>
            </button>
          )}
        </div>
      </section>
      <section className="alice-agenda-tasks">
        <button className="alice-agenda-heading" onClick={onTasks}>
          <ListTodo size={16} />
          <span>{t("To do", "待办")}</span>
          <ChevronRight size={14} />
        </button>
        <div className="alice-agenda-rows">
          {tasks.length ? (
            tasks.map((task) => (
              <button key={task.id} onClick={onTasks}>
                <i aria-hidden="true" />
                <span>{task.title}</span>
              </button>
            ))
          ) : (
            <button onClick={onTasks}>
              <span>
                {privateVisible && data.tasks.active_count === 0
                  ? t("Nothing pending", "暂无待办")
                  : t("View tasks", "查看待办")}
              </span>
            </button>
          )}
        </div>
      </section>
    </aside>
  );
}
