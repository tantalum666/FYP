import { useEffect, useState } from "react";
import { DateTime } from "luxon";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Circle,
  LogOut,
  Monitor,
  Plus,
} from "lucide-react";
import { errorText, pendingWrite, request, write } from "../api";
import { eventTime, inZone, locale, title } from "../dates";
import type {
  Language,
  Occurrence,
  RecordEntry,
  Settings,
  Snapshot,
  Translate,
} from "../types";

export function TodayView({
  snapshot,
  language,
  now,
  onNew,
  onOpen,
  onCalendar,
  onDevice,
  t,
}: {
  snapshot: Snapshot;
  language: Language;
  now: DateTime;
  onNew: () => void;
  onOpen: (event: Occurrence) => void;
  onCalendar: () => void;
  onDevice: () => void;
  t: Translate;
}) {
  const zone = snapshot.settings.timezone;
  const events = snapshot.occurrences;
  const upcoming =
    events.find(
      (e) => !e.completed && !e.all_day && inZone(e.end, zone) > now,
    ) ?? events.find((e) => !e.completed && e.all_day);
  return (
    <div className="today-view">
      <header className="page-heading">
        <div>
          <h1>{t("Today", "今天")}</h1>
          <p>
            {now
              .setLocale(locale(language))
              .toFormat(language === "en" ? "cccc, d LLLL" : "M月d日 cccc")}
          </p>
        </div>
        <button className="add-today" onClick={onNew}>
          <span>
            <Plus />
          </span>
          {t("Add", "添加")}
        </button>
      </header>
      {snapshot.has_samples && (
        <p className="sample-note">{t("Example calendar", "含示例日程")}</p>
      )}
      <div className="today-clock">
        <span>{now.toFormat("HH:mm")}</span>
        <small>{zone.replaceAll("_", " ").split("/").at(-1)}</small>
      </div>
      <div className="today-columns">
        <section className="next-section">
          <h2>{t("Up next", "接下来")}</h2>
          {upcoming ? (
            <button
              className={`next-event ${upcoming.color}`}
              onClick={() => onOpen(upcoming)}
            >
              <span>
                <strong>{title(upcoming, language)}</strong>
                <span>{eventTime(upcoming, zone, language)}</span>
                <small>
                  {upcoming.calendar === "study"
                    ? t("Study", "学习")
                    : t("Personal", "个人")}
                </small>
              </span>
              <ChevronRight />
            </button>
          ) : (
            <div className="empty-next">
              <strong>
                {t("A little breathing room.", "留一点从容的时间。")}
              </strong>
              <p>{t("No upcoming events today.", "今天没有待进行的日程。")}</p>
              <button className="text-button" onClick={onNew}>
                {t("Add an event", "添加日程")}
                <Plus size={16} />
              </button>
            </div>
          )}
        </section>
        <section className="agenda-section">
          <div className="section-heading">
            <h2>{t("Your schedule", "今日安排")}</h2>
            <button className="text-button" onClick={onCalendar}>
              {t("View calendar", "查看日历")}
              <ChevronRight size={16} />
            </button>
          </div>
          {events.length === 0 && (
            <p className="empty-text">
              {t("Your day is yours to plan.", "从添加第一件事开始安排今天。")}
            </p>
          )}
          {events.map((e) => (
            <button
              className={`agenda-row ${e.completed ? "completed" : ""}`}
              key={e.id + e.occurrence_key}
              onClick={() => onOpen(e)}
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
                  {eventTime(e, zone, language)} ·{" "}
                  {e.calendar === "study"
                    ? t("Study", "学习")
                    : t("Personal", "个人")}
                </small>
              </span>
              {e.completed && <Check size={17} />}
            </button>
          ))}
        </section>
      </div>
      <button className="desk-status-row" onClick={onDevice}>
        <Monitor />
        <span>
          <strong>{t("Desk status", "设备状态")}</strong>
          <small>{t("Camera not connected", "摄像头未连接")}</small>
        </span>
        <ChevronRight size={18} />
      </button>
    </div>
  );
}

export function RecordsView({
  revision,
  language,
  zone,
  t,
}: {
  revision: number;
  language: Language;
  zone: string;
  t: Translate;
}) {
  const [rows, setRows] = useState<RecordEntry[]>([]),
    [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState("all");
  useEffect(() => {
    let active = true;
    request<{ records: RecordEntry[] }>("/records")
      .then((r) => {
        if (active) {
          setRows(r.records);
          setError(null);
        }
      })
      .catch((e) => {
        if (active) setError(e);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  const actionName: Record<string, [string, string]> = {
    created: ["Event created", "已创建日程"],
    update: ["Event updated", "已修改日程"],
    delete: ["Event removed", "已删除日程"],
    complete: ["Marked complete", "已标记完成"],
    reopen: ["Marked incomplete", "已取消完成"],
    acknowledge: ["Reminder acknowledged", "已确认提醒"],
    snooze: ["Reminder snoozed", "已延后提醒"],
    settings_updated: ["Settings updated", "已更新设置"],
  };
  return (
    <div className="standard-page">
      <header className="page-heading">
        <div>
          <h1>{t("Records", "记录")}</h1>
          <p>
            {t(
              "Your changes and reminders, in one place.",
              "在这里查看日程变更和提醒记录。",
            )}
          </p>
        </div>
      </header>
      <div className="records-toolbar">
        <label>
          {t("Show", "查看")}
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">{t("All activity", "全部活动")}</option>
            <option value="events">{t("Calendar changes", "日程变更")}</option>
            <option value="reminders">
              {t("Reminder actions", "提醒操作")}
            </option>
          </select>
        </label>
        <span>{t("Latest 200 entries", "最近 200 条")}</span>
      </div>
      {error ? (
        <p className="error-message">{errorText(error, t)}</p>
      ) : (
        <div className="activity-list">
          {rows
            .filter(
              (r) =>
                filter === "all" ||
                (filter === "reminders"
                  ? ["acknowledge", "snooze"].includes(r.action)
                  : [
                      "created",
                      "update",
                      "delete",
                      "complete",
                      "reopen",
                    ].includes(r.action)),
            )
            .map((r) => (
              <div className="activity-row" key={r.sequence}>
                <span className="activity-icon">
                  <Circle size={12} />
                </span>
                <div>
                  <strong>
                    {t(...(actionName[r.action] ?? ["Activity", "活动"]))}
                  </strong>
                  <p>
                    {r.title === "" ? t("Private event", "私人事项") : r.title}
                  </p>
                </div>
                <time>
                  {inZone(r.at, zone)
                    .setLocale(locale(language))
                    .toFormat("d LLL · HH:mm")}
                </time>
              </div>
            ))}
          {rows.length === 0 && (
            <p className="empty-text">
              {t(
                "Your first change will appear here.",
                "第一条操作记录将显示在这里。",
              )}
            </p>
          )}
        </div>
      )}
      <p className="footnote">
        {t(
          "Posture records will appear after a camera is connected and calibrated.",
          "接入摄像头并完成标定后，这里将加入坐姿记录。",
        )}
      </p>
    </div>
  );
}

export function DeviceView({
  settings,
  language,
  setLanguage,
  onSaved,
  onLogout,
  onDeviceLayout,
  t,
}: {
  settings: Settings;
  language: Language;
  setLanguage: (l: Language) => void;
  onSaved: () => void;
  onLogout: () => void;
  onDeviceLayout: () => void;
  t: Translate;
}) {
  const [zone, setZone] = useState(settings.timezone),
    [hidden, setHidden] = useState(settings.hide_private),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [saved, setSaved] = useState(false);
  useEffect(() => {
    setZone(settings.timezone);
    setHidden(settings.hide_private);
  }, [settings.version]);
  async function save() {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await write("/settings", {
        expected_version: settings.version,
        timezone: zone,
        hide_private: hidden,
      });
      setSaved(true);
      onSaved();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="standard-page">
      <header className="page-heading">
        <div>
          <h1>{t("Device", "设备")}</h1>
          <p>
            {t(
              "A quieter desk. Your preferences.",
              "让桌面更从容，按你的习惯设置。",
            )}
          </p>
        </div>
      </header>
      <section className="settings-section">
        <h2>{t("Workspace", "工作空间")}</h2>
        <div className="setting-row">
          <span>
            <strong>{t("Language", "语言")}</strong>
            <small>{t("Saved on this screen", "保存在当前界面")}</small>
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            aria-label={t("Language", "语言")}
          >
            <option value="en">English</option>
            <option value="zh">简体中文</option>
          </select>
        </div>
        <div className="setting-row">
          <label htmlFor="timezone">
            <strong>{t("Calendar timezone", "日历时区")}</strong>
            <small>
              {t("Shared across your connected screens", "在已连接界面间共用")}
            </small>
          </label>
          <select
            id="timezone"
            value={zone}
            onChange={(e) => {
              setZone(e.target.value);
              setSaved(false);
            }}
          >
            {[
              "Asia/Hong_Kong",
              "Asia/Shanghai",
              "Asia/Tokyo",
              "Europe/London",
              "America/New_York",
              "UTC",
              ...(![
                "Asia/Hong_Kong",
                "Asia/Shanghai",
                "Asia/Tokyo",
                "Europe/London",
                "America/New_York",
                "UTC",
              ].includes(zone)
                ? [zone]
                : []),
            ].map((z) => (
              <option key={z}>{z}</option>
            ))}
          </select>
        </div>
        <div className="setting-row">
          <label htmlFor="hide-private">
            <strong>{t("Hide private details", "隐藏私人详情")}</strong>
            <small>
              {t(
                "Show titles as “Private event” on connected screens",
                "在已连接界面将标题显示为“私人事项”",
              )}
            </small>
          </label>
          <input
            id="hide-private"
            type="checkbox"
            checked={hidden}
            onChange={(e) => {
              setHidden(e.target.checked);
              setSaved(false);
            }}
          />
        </div>
        {!!error && <p className="error-message">{errorText(error, t)}</p>}
        <div className="settings-save">
          <button className="primary" disabled={busy} onClick={save}>
            {busy ? t("Saving…", "保存中…") : t("Save preferences", "保存偏好")}
          </button>
          {saved && <span role="status">{t("Saved", "已保存")}</span>}
        </div>
      </section>
      <section className="settings-section">
        <h2>{t("Desk connections", "桌面连接")}</h2>
        {[
          [
            t("Camera & posture", "摄像头与坐姿"),
            t("Not connected · calibration required", "未连接 · 需要标定"),
          ],
          [t("Voice assistant", "语音助理"), t("Not connected", "未接入")],
          [t("Robotic arm", "机械臂"), t("Not connected", "未连接")],
          [t("Weather", "天气"), t("Not connected", "未接入")],
          [t("External calendars", "外部日历"), t("Not connected", "未接入")],
        ].map(([name, state]) => (
          <div className="connection-row" key={name}>
            <span>{name}</span>
            <small>{state}</small>
          </div>
        ))}
        <p className="footnote">
          {t(
            "Calendar reminders appear on screen while this local service is running. Phone background notifications and physical outputs are not connected yet.",
            "本地服务运行时，日历提醒显示在界面内。手机后台通知及实体输出尚未接入。",
          )}
        </p>
        <button className="secondary" onClick={onDeviceLayout}>
          {t("Open device layout", "打开设备布局")}
          <ArrowUpRight size={16} />
        </button>
      </section>
      <section className="settings-section">
        <h2>{t("Account", "账号")}</h2>
        <div className="setting-row">
          <span>
            <strong>owner</strong>
            <small>{t("Local workspace", "本地工作空间")}</small>
          </span>
          <button
            className="secondary"
            onClick={onLogout}
            disabled={!!pendingWrite()}
          >
            <LogOut size={16} />
            {t("Sign out", "退出")}
          </button>
        </div>
      </section>
    </div>
  );
}
