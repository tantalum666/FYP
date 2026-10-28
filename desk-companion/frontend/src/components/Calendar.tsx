import { useEffect, useRef } from "react";
import { DateTime } from "luxon";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  LockKeyhole,
  Plus,
  Repeat2,
} from "lucide-react";
import {
  dayISO,
  eventTime,
  inZone,
  locale,
  monthDays,
  occursOn,
  title,
} from "../dates";
import type { Language, Occurrence, Translate, View } from "../types";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { busyMinutes, lunarDate } from "../workspace/calendarExtras";

export function MiniMonth({
  anchor,
  selected,
  language,
  onSelect,
  onMonth,
}: {
  anchor: DateTime;
  selected: DateTime;
  language: Language;
  onSelect: (day: DateTime) => void;
  onMonth: (offset: number) => void;
}) {
  const days = monthDays(anchor).slice(
    0,
    Math.ceil(
      (anchor.startOf("month").weekday - 1 + (anchor.daysInMonth ?? 31)) / 7,
    ) * 7,
  );
  return (
    <section
      className="mini-month"
      aria-label={language === "en" ? "Date picker" : "日期选择"}
    >
      <div className="mini-heading">
        <strong>
          {anchor
            .setLocale(locale(language))
            .toFormat(language === "en" ? "LLLL yyyy" : "yyyy年M月")}
        </strong>
        <span>
          <button
            className="icon-button small"
            aria-label={language === "en" ? "Previous month" : "上个月"}
            onClick={() => onMonth(-1)}
          >
            <ChevronLeft />
          </button>
          <button
            className="icon-button small"
            aria-label={language === "en" ? "Next month" : "下个月"}
            onClick={() => onMonth(1)}
          >
            <ChevronRight />
          </button>
        </span>
      </div>
      <div className="mini-grid">
        {days.slice(0, 7).map((d) => (
          <span className="weekday" key={d.weekday}>
            {language === "en"
              ? d.toFormat("ccccc")
              : ["一", "二", "三", "四", "五", "六", "日"][d.weekday - 1]}
          </span>
        ))}
        {days.map((d) => (
          <button
            key={dayISO(d)}
            onClick={() => onSelect(d)}
            aria-label={d.toISODate()!}
            aria-pressed={dayISO(d) === dayISO(selected)}
            className={`${d.month !== anchor.month ? "outside" : ""} ${dayISO(d) === dayISO(selected) ? "selected" : ""}`}
          >
            {d.day}
          </button>
        ))}
      </div>
    </section>
  );
}

function EventBlock({
  event,
  zone,
  language,
  onOpen,
  compact = false,
  style,
}: {
  event: Occurrence;
  zone: string;
  language: Language;
  onOpen: (e: Occurrence) => void;
  compact?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <button
      style={style}
      className={`event-block ${event.color} ${event.completed ? "completed" : ""} ${compact ? "compact" : ""}`}
      onClick={() => onOpen(event)}
      aria-label={`${title(event, language)}, ${eventTime(event, zone, language)}`}
    >
      <span className="event-title">
        {event.completed && <Check size={13} />}
        {title(event, language)}
      </span>
      {!compact && (
        <span className="event-time">{eventTime(event, zone, language)}</span>
      )}
      <span className="event-flags">
        {event.conflicts.length > 0 && (
          <CircleAlert
            size={13}
            aria-label={language === "en" ? "Time conflict" : "时间冲突"}
          />
        )}
        {event.series_recurrence.frequency !== "none" && <Repeat2 size={12} />}
        {event.visibility === "private" && <LockKeyhole size={11} />}
      </span>
    </button>
  );
}

export function CalendarToolbar({
  anchor,
  view,
  setView,
  onNavigate,
  onToday,
  onNew,
  language,
  zone,
  t,
}: {
  anchor: DateTime;
  view: View;
  setView: (view: View) => void;
  onNavigate: (n: number) => void;
  onToday: () => void;
  onNew: () => void;
  language: Language;
  zone: string;
  t: Translate;
}) {
  const first = anchor.startOf("week").setLocale(locale(language));
  return (
    <header className="calendar-toolbar">
      <div className="toolbar-main">
        <div>
          <h1>
            {anchor
              .setLocale(locale(language))
              .toFormat(language === "en" ? "LLLL yyyy" : "yyyy年M月")}
          </h1>
          <p>
            {view === "week"
              ? `${first.toFormat(language === "en" ? "d LLL" : "M月d日")} – ${first.plus({ days: 6 }).toFormat(language === "en" ? "d LLL" : "M月d日")}`
              : view === "day"
                ? anchor
                    .setLocale(locale(language))
                    .toFormat(language === "en" ? "cccc, d LLL" : "M月d日 cccc")
                : t(
                    "A little room for everything.",
                    "让每件事都有合适的时间。",
                  )}
          </p>
        </div>
        <div className="toolbar-actions">
          <div className="segments" aria-label={t("Calendar view", "日历视图")}>
            {(["day", "week", "month"] as View[]).map((v, i) => (
              <button
                key={v}
                aria-pressed={view === v}
                className={view === v ? "selected" : ""}
                onClick={() => setView(v)}
              >
                {language === "en"
                  ? ["Day", "Week", "Month"][i]
                  : ["日", "周", "月"][i]}
              </button>
            ))}
          </div>
          <button className="primary" onClick={onNew}>
            <Plus size={18} />
            <span>{t("New event", "新建日程")}</span>
          </button>
        </div>
      </div>
      <div className="toolbar-secondary">
        <div className="date-controls">
          <button
            className="icon-button"
            aria-label={t("Previous period", "上一时段")}
            onClick={() => onNavigate(-1)}
          >
            <ChevronLeft />
          </button>
          <button className="secondary" onClick={onToday}>
            {t("Today", "今天")}
          </button>
          <button
            className="icon-button"
            aria-label={t("Next period", "下一时段")}
            onClick={() => onNavigate(1)}
          >
            <ChevronRight />
          </button>
        </div>
        <span className="zone-label">
          {zone.replaceAll("_", " ").split("/").at(-1)}
        </span>
      </div>
    </header>
  );
}

export function MonthGrid({
  anchor,
  events,
  zone,
  language,
  onOpen,
  onDay,
  t,
}: {
  anchor: DateTime;
  events: Occurrence[];
  zone: string;
  language: Language;
  onOpen: (event: Occurrence) => void;
  onDay: (date: DateTime) => void;
  t: Translate;
}) {
  const extras = useWorkspace().data?.calendar_extras;
  const days = monthDays(anchor);
  const today = DateTime.now().setZone(zone).toISODate();
  return (
    <div className="month-view">
      <div className="month-weekdays">
        {days.slice(0, 7).map((d) => (
          <div key={d.weekday}>
            {d.setLocale(locale(language)).toFormat("ccc")}
          </div>
        ))}
      </div>
      <div className="month-grid">
        {days.map((day) => {
          const found = events.filter((e) => occursOn(e, day, zone));
          return (
            <div
              key={dayISO(day)}
              className={`month-cell ${day.month !== anchor.month ? "outside" : ""} ${day.weekday > 5 ? "weekend" : ""}`}
            >
              <button
                className={`day-number ${dayISO(day) === today ? "today" : ""}`}
                onClick={() => onDay(day)}
                aria-label={t("Open ", "打开 ") + dayISO(day)}
              >
                {day.day}
              </button>
              {extras?.preferences.show_lunar && (
                <span className="month-lunar">
                  {lunarDate(day, language, true)}
                </span>
              )}
              {extras?.holidays[language][dayISO(day)] && (
                <span
                  className="month-holiday"
                  title={extras.holidays[language][dayISO(day)]}
                >
                  {extras.holidays[language][dayISO(day)]}
                </span>
              )}
              <span className="month-availability">
                {busyMinutes(found, day) > 0
                  ? `${Math.round(busyMinutes(found, day) / 6) / 10}h ${t("busy", "占用")}`
                  : t("No recorded busy time", "无已记录占用")}
              </span>
              <div className="month-events">
                {found.slice(0, 3).map((e) => (
                  <EventBlock
                    key={e.id + e.occurrence_key}
                    event={e}
                    zone={zone}
                    language={language}
                    onOpen={onOpen}
                    compact
                  />
                ))}
                {found.length > 3 && (
                  <button
                    className="text-button more-events"
                    onClick={() => onDay(day)}
                  >
                    +{found.length - 3} {t("more", "项")}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function placeEvents(events: Occurrence[], day: DateTime, zone: string) {
  const start = day.startOf("day");
  const finish = start.plus({ days: 1 });
  const items = events
    .map((event) => {
      const originalStart = inZone(event.start, zone),
        originalEnd = inZone(event.end, zone);
      const s =
        originalStart < start
          ? 0
          : originalStart.hour * 60 + originalStart.minute;
      const e =
        originalEnd >= finish
          ? 1440
          : originalEnd.hour * 60 + originalEnd.minute;
      return { event, start: s, end: Math.max(e, s + 15), column: 0, total: 1 };
    })
    .sort((a, b) => a.start - b.start || b.end - a.end);
  let group: typeof items = [],
    groupEnd = -1;
  const finishGroup = () => {
    const ends: number[] = [];
    group.forEach((item) => {
      let col = ends.findIndex((end) => end <= item.start);
      if (col < 0) col = ends.length;
      ends[col] = item.end;
      item.column = col;
    });
    group.forEach((item) => {
      item.total = ends.length;
    });
  };
  for (const item of items) {
    if (item.start >= groupEnd) {
      finishGroup();
      group = [];
      groupEnd = -1;
    }
    group.push(item);
    groupEnd = Math.max(groupEnd, item.end);
  }
  finishGroup();
  return items;
}

export function TimeGrid({
  anchor,
  view,
  events,
  zone,
  language,
  onOpen,
  onDay,
  initialHour = 8,
  t,
}: {
  anchor: DateTime;
  view: "week" | "day";
  events: Occurrence[];
  zone: string;
  language: Language;
  onOpen: (event: Occurrence) => void;
  onDay: (date: DateTime) => void;
  initialHour?: number;
  t: Translate;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const first = anchor.startOf(view === "week" ? "week" : "day");
  const days = Array.from({ length: view === "week" ? 7 : 1 }, (_, i) =>
    first.plus({ days: i }),
  );
  const today = DateTime.now().setZone(zone).toISODate();
  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = initialHour * 64;
  }, [view, anchor.toISODate(), initialHour]);
  return (
    <div className={`time-view ${view}`}>
      <div
        className="time-grid-head"
        style={{
          gridTemplateColumns: `60px repeat(${days.length}, minmax(0,1fr))`,
        }}
      >
        <div />
        {days.map((d) => (
          <button
            key={dayISO(d)}
            onClick={() => onDay(d)}
            className={d.weekday > 5 ? "weekend" : ""}
            aria-label={d
              .setLocale(locale(language))
              .toFormat(language === "en" ? "ccc d LLL" : "M月d日 ccc")}
          >
            <span>{d.setLocale(locale(language)).toFormat("ccc")}</span>
            <span>
              {language === "zh" && `${d.month}月`}
              <b className={dayISO(d) === today ? "today" : ""}>{d.day}</b>
              {language === "en" ? " " : ""}
              {language === "zh"
                ? "日"
                : d.setLocale(locale(language)).toFormat("LLL")}
            </span>
          </button>
        ))}
      </div>
      <div
        className="all-day-grid"
        style={{
          gridTemplateColumns: `60px repeat(${days.length}, minmax(0,1fr))`,
        }}
      >
        <div className="all-day-label">{t("All day", "全天")}</div>
        {days.map((d) => (
          <div key={dayISO(d)} className={d.weekday > 5 ? "weekend" : ""}>
            {events
              .filter((e) => e.all_day && occursOn(e, d, zone))
              .map((e) => (
                <EventBlock
                  key={e.id + e.occurrence_key}
                  event={e}
                  zone={zone}
                  language={language}
                  onOpen={onOpen}
                  compact
                />
              ))}
          </div>
        ))}
      </div>
      <div className="time-scroll" ref={scroller}>
        <div
          className="time-grid-body"
          style={{
            gridTemplateColumns: `60px repeat(${days.length}, minmax(0,1fr))`,
          }}
        >
          <div className="time-axis">
            {Array.from({ length: 24 }, (_, h) => (
              <div key={h}>{String(h).padStart(2, "0")}:00</div>
            ))}
          </div>
          {days.map((d) => (
            <div
              key={dayISO(d)}
              className={`time-column ${d.weekday > 5 ? "weekend" : ""}`}
            >
              {placeEvents(
                events.filter((e) => !e.all_day && occursOn(e, d, zone)),
                d,
                zone,
              ).map((item) => (
                <EventBlock
                  key={item.event.id + item.event.occurrence_key}
                  event={item.event}
                  zone={zone}
                  language={language}
                  onOpen={onOpen}
                  style={{
                    top: (item.start / 60) * 64 + 2,
                    height: Math.max(
                      25,
                      ((item.end - item.start) / 60) * 64 - 4,
                    ),
                    left: `calc(${(item.column / item.total) * 100}% + 3px)`,
                    width: `calc(${100 / item.total}% - 6px)`,
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
