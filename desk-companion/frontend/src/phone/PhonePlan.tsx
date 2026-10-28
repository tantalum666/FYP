import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ListTodo,
  Plus,
} from "lucide-react";
import { dayISO, eventTime, locale, title } from "../dates";
import type { EventInput, Language, Occurrence, Translate } from "../types";
import { useDraftState } from "../components/DraftGuard";
import { MonthGrid } from "../components/Calendar";
import { TaskPanel } from "../workspace/TaskPanel";
import type { usePhoneCalendar } from "./usePhoneCalendar";

export function PhonePlan({
  calendar,
  t,
  language,
  offline,
  planTab,
  setPlanTab,
  onNew,
  onOpen,
  onPlan,
  onDiscuss,
}: {
  calendar: ReturnType<typeof usePhoneCalendar>;
  t: Translate;
  language: Language;
  offline: boolean;
  planTab: "calendar" | "tasks";
  setPlanTab: (tab: "calendar" | "tasks") => void;
  onNew: () => void;
  onOpen: (event: Occurrence) => void;
  onPlan: (event: EventInput) => void;
  onDiscuss: (id: string, title: string) => void;
}) {
  const guard = useDraftState();
  const changingBlocked = guard.dirty || guard.busy;
  const {
    date,
    setDate,
    month,
    setMonth,
    anchor,
    zone,
    todayKey,
    snapshot,
    daysEvents,
  } = calendar;
  return (
    <>
      <div
        className="phone-segments"
        role="group"
        aria-label={t("Plan section", "计划分类")}
      >
        <button
          aria-pressed={planTab === "calendar"}
          disabled={planTab !== "calendar" && changingBlocked}
          onClick={() => setPlanTab("calendar")}
        >
          <CalendarDays size={17} />
          {t("Calendar", "日历")}
        </button>
        <button
          aria-pressed={planTab === "tasks"}
          disabled={planTab !== "tasks" && changingBlocked}
          onClick={() => setPlanTab("tasks")}
        >
          <ListTodo size={17} />
          {t("Tasks", "事务")}
        </button>
      </div>
      {changingBlocked && (
        <p className="phone-plan-edit-status" role="status">
          {t(
            "Save or discard your current edit before changing sections.",
            "切换分类前，请先保存或放弃当前编辑。",
          )}
        </p>
      )}
      {planTab === "tasks" ? (
        <TaskPanel t={t} zone={zone} onPlan={onPlan} onDiscuss={onDiscuss} />
      ) : (
        <>
          <div className="phone-plan-toolbar">
            <button
              className="text-button"
              onClick={() => {
                setDate(todayKey);
                setMonth(false);
              }}
            >
              {t("Today", "今天")}
            </button>
            <button
              className="text-button"
              aria-pressed={month}
              onClick={() => setMonth(!month)}
            >
              {month ? t("Day list", "当天列表") : t("Month", "月历")}
            </button>
            <button className="primary" onClick={() => onNew()}>
              <Plus size={17} />
              {t("New", "新增")}
            </button>
          </div>
          <div className="phone-date-row">
            <button
              className="icon-button"
              aria-label={t("Previous date", "上一日期")}
              onClick={() =>
                setDate(
                  dayISO(anchor.minus(month ? { months: 1 } : { days: 1 })),
                )
              }
            >
              <ChevronLeft />
            </button>
            <label>
              <span>
                {anchor
                  .setLocale(locale(language))
                  .toFormat(language === "zh" ? "yyyy年M月d日" : "d MMMM yyyy")}
              </span>
              <input
                type="date"
                aria-label={t("Choose date", "选择日期")}
                value={date}
                onChange={(e) => {
                  if (e.target.value) setDate(e.target.value);
                }}
              />
            </label>
            <button
              className="icon-button"
              aria-label={t("Next date", "下一日期")}
              onClick={() =>
                setDate(
                  dayISO(anchor.plus(month ? { months: 1 } : { days: 1 })),
                )
              }
            >
              <ChevronRight />
            </button>
          </div>
          {month && snapshot && (
            <MonthGrid
              anchor={anchor}
              events={snapshot.occurrences}
              zone={zone}
              language={language}
              onOpen={onOpen}
              onDay={(day) => {
                setDate(dayISO(day));
                setMonth(false);
              }}
              t={t}
            />
          )}
          <div className="phone-agenda">
            {daysEvents === null ? (
              <p role="status">{t("Loading your day…", "正在读取当天安排…")}</p>
            ) : daysEvents.length ? (
              daysEvents.map((event) => (
                <button
                  key={event.id + event.occurrence_key}
                  onClick={() => onOpen(event)}
                  className={`phone-event ${event.completed ? "completed" : ""}`}
                >
                  <span>{eventTime(event, zone, language)}</span>
                  <strong>{title(event, language)}</strong>
                  <small>
                    {event.completed
                      ? t("Completed", "已完成")
                      : event.location ||
                        (event.calendar === "study"
                          ? t("Study", "学习")
                          : t("Personal", "个人"))}
                    {event.conflicts.length > 0 &&
                      t(" · Time conflict", " · 时间冲突")}
                  </small>
                  <ChevronRight size={18} />
                </button>
              ))
            ) : (
              <div className="phone-empty">
                <CalendarDays size={28} />
                <h3>{t("A little room in your day.", "这天还有一些空闲。")}</h3>
                <p>
                  {t(
                    "Add something when you have a plan.",
                    "有新计划时，随手记下来。",
                  )}
                </p>
                <button className="secondary" onClick={() => onNew()}>
                  {t("Add an event", "添加日程")}
                </button>
              </div>
            )}
          </div>
          <p className="phone-zone">
            {zone}
            {offline ? t(" · May be out of date", " · 可能不是最新状态") : ""}
          </p>
        </>
      )}
    </>
  );
}
