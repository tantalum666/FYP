import { PermissionsPanel } from "../workspace/PermissionsPanel";
import { ExportLink } from "../workspace/ExportLink";
import { useDraftGuard } from "./DraftGuard";
import { useEffect, useId, useState } from "react";
import { DateTime } from "luxon";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Circle,
  Monitor,
  Plus,
  Camera,
  Link2,
  SlidersHorizontal,
  Sparkles,
  ListTodo,
} from "lucide-react";
import { isNative } from "../native";
import { PhoneFeatures } from "../workspace/PhoneFeatures";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { lunarDate } from "../workspace/calendarExtras";
import { feedbackText, postureLabel } from "../workspace/PosturePanel";
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
  onTasks: () => void;
  t: Translate;
}) {
  const zone = snapshot.settings.timezone;
  const workspace = useWorkspace();
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
      <div className="today-at-a-glance">
        {workspace.data?.calendar_extras.preferences.show_lunar && (
          <span>{lunarDate(now, language)}</span>
        )}
        {workspace.data?.calendar_extras.holidays[language][
          now.toISODate()!
        ] && (
          <span>
            {
              workspace.data.calendar_extras.holidays[language][
                now.toISODate()!
              ]
            }
          </span>
        )}
        {workspace.data?.calendar_extras.weather.temperature_c !==
          undefined && (
          <span>
            {workspace.data.calendar_extras.weather.temperature_c}°C ·{" "}
            {t("Hong Kong", "香港")}
            {workspace.data.calendar_extras.weather.status === "stale"
              ? t(" · Last reading", " · 上次观测")
              : ""}
          </span>
        )}
      </div>
      <div className="today-clock">
        <span>{now.toFormat("HH:mm")}</span>
        <small>{zone.replaceAll("_", " ").split("/").at(-1)}</small>
      </div>
      <div className={`today-columns ${events.length ? "" : "is-empty"}`}>
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
        {events.length > 0 && (
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
                {t(
                  "Your day is yours to plan.",
                  "从添加第一件事开始安排今天。",
                )}
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
        )}
      </div>
      <button className="desk-status-row" onClick={onDevice}>
        <Monitor />
        <span>
          <strong>{t("Desk status", "设备状态")}</strong>
          <small>
            {workspace.offline
              ? t("Desk connection lost", "桌面连接中断")
              : postureLabel(workspace.data?.posture, t)}
          </small>
        </span>
        <ChevronRight size={18} />
      </button>
      {!!workspace.data?.tasks?.active_count &&
        !workspace.offline &&
        !workspace.stale && (
          <button
            className="desk-status-row today-task-summary"
            onClick={onTasks}
          >
            <ListTodo />
            <span>
              <strong>
                {workspace.data.tasks.due_count
                  ? t(
                      `${workspace.data.tasks.due_count} task check-in${workspace.data.tasks.due_count === 1 ? "" : "s"} ready`,
                      `${workspace.data.tasks.due_count}项事务待跟进`,
                    )
                  : t("Keep your next step in view", "继续推进下一步")}
              </strong>
              <small>
                {t(
                  `${workspace.data.tasks.active_count} active task${workspace.data.tasks.active_count === 1 ? "" : "s"} · Review progress`,
                  `${workspace.data.tasks.active_count}项未完成事务 · 查看进展`,
                )}
              </small>
            </span>
            <ChevronRight size={18} />
          </button>
        )}
      {workspace.data?.posture.feedback &&
        !workspace.offline &&
        now.toSeconds() - workspace.data.posture.feedback.created_at < 180 && (
          <button className="posture-notice" onClick={onDevice}>
            <Camera />
            <span>
              <strong>
                {feedbackText(workspace.data.posture.feedback.kind, t)}
              </strong>
              <p>
                {workspace.data.posture.source === "replay"
                  ? t("Replay feedback · open to review", "回放反馈 · 点击查看")
                  : t("Open posture feedback", "查看坐姿反馈")}
              </p>
            </span>
            <ChevronRight />
          </button>
        )}
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
    [error, setError] = useState<unknown>(null),
    [kind, setKind] = useState("all"),
    [source, setSource] = useState("all"),
    [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const query = new URLSearchParams({
    kind,
    source,
    ...(start ? { start } : {}),
    ...(end ? { end } : {}),
  }).toString();
  const [loading, setLoading] = useState(true);
  const [loadedQuery, setLoadedQuery] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filterId = useId();
  const activeFilters =
    Number(kind !== "all") +
    Number(source !== "all") +
    Number(!!start) +
    Number(!!end);
  const currentRows = loadedQuery === query ? rows : [];
  useEffect(() => {
    let alive = true;
    setLoading(true);
    void request<{ records: RecordEntry[] }>(`/records?${query}`)
      .then((result) => {
        if (alive) {
          setRows(result.records);
          setLoadedQuery(query);
          setError(null);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (alive) {
          setError(e);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [revision, query]);
  const labels: Record<string, [string, string]> = {
    task_created: ["Task created", "事务已创建"],
    task_update: ["Task updated", "事务已更新"],
    task_note: ["Progress recorded", "进展已记录"],
    task_complete: ["Task completion confirmed", "事务完成已确认"],
    task_cancel: ["Task cancelled", "事务已取消"],
    task_reopen: ["Task reopened", "事务已恢复"],
    task_pause: ["Task follow-ups paused", "事务跟进已暂停"],
    task_resume: ["Task follow-ups resumed", "事务跟进已恢复"],
    task_snooze: ["Task check-in postponed", "事务检查已延后"],
    task_followup: ["Task check-in ready", "事务待更新进展"],
    task_restored: ["Task restored from backup", "事务已从备份恢复"],
    created: ["Event created", "已创建日程"],
    update: ["Event updated", "已修改日程"],
    delete: ["Event removed", "已删除日程"],
    complete: ["Marked complete", "已标记完成"],
    reopen: ["Marked incomplete", "已取消完成"],
    acknowledge: ["Reminder acknowledged", "已确认提醒"],
    snooze: ["Reminder snoozed", "已延后提醒"],
    posture_prompt: ["Position prompt", "坐姿提示"],
    posture_reassessment: ["Position rechecked", "坐姿复测"],
    calibration_saved: ["Reference saved", "已保存个人参考"],
    movement_prompt: ["Movement reminder", "活动提醒"],
    posture_configure: ["Observation preferences updated", "已更新观察偏好"],
    posture_pause: ["Observation paused", "已暂停观察"],
    posture_resume: ["Observation resumed", "已恢复观察"],
    assistant_draft: ["Assistant draft prepared", "已生成助理草稿"],
    assistant_confirmed: ["Assistant change saved", "已保存助理操作"],
    assistant_cancelled: ["Assistant draft cancelled", "已取消助理草稿"],
    memory_saved: ["Memory saved", "记忆已保存"],
    memory_replaced: ["Memory corrected", "记忆已更正"],
    memory_deleted: ["Memory removed", "记忆已删除"],
    persona_replace: ["Assistant style updated", "助理风格已更新"],
    persona_reset: ["Assistant style reset", "助理风格已重置"],
    device_paired: ["Screen paired", "已配对终端"],
    device_revoked: ["Screen access revoked", "已撤销终端"],
    output_queued: ["Output queued", "反馈已排队"],
    output_executed: ["Driver reported completion", "驱动报告完成"],
    output_simulated: ["Output simulated", "反馈已模拟"],
    output_failed: ["Output failed", "反馈失败"],
    voice_session: ["Voice session ended", "语音会话结束"],
    calendar_imported: ["Calendar imported", "已导入日历"],
    share_created: ["Read-only link created", "已创建只读链接"],
    share_revoked: ["Read-only link revoked", "已撤销只读链接"],
    settings_updated: ["Settings updated", "已更新设置"],
    workspace_preferences_updated: ["Preferences updated", "已更新偏好"],
    announcement_claimed: ["Reminder delivered to display", "提醒已交给屏幕"],
  };
  const outcomes: Record<string, [string, string]> = {
    adjusted: ["Back within reference", "回到个人参考范围"],
    still_deviated: ["Deviation still observed", "仍观察到偏离"],
    unknown: ["Unable to reassess", "无法复测"],
    waiting: ["Awaiting new observations", "等待新的观察"],
  };
  return (
    <div className="standard-page">
      <header className="page-heading">
        <div>
          <h1>{t("Records", "记录")}</h1>
          <p>
            {t(
              "Calendar changes, observations and actual action results.",
              "查看日历变更、观察与实际操作结果。",
            )}
          </p>
        </div>
      </header>
      <div className="records-filter-summary">
        <span>
          {loading
            ? t("Loading records…", "正在读取记录…")
            : error
              ? t("Records unavailable", "暂时无法读取记录")
              : t(
                  `${currentRows.length} recent record${currentRows.length === 1 ? "" : "s"}`,
                  `${currentRows.length}条最近记录`,
                )}
        </span>
        <div className="workspace-inline-actions">
          <button
            className="secondary"
            aria-expanded={filtersOpen}
            aria-controls={filterId}
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            <SlidersHorizontal size={16} />
            {t("Filters", "筛选")}
            {activeFilters ? ` (${activeFilters})` : ""}
          </button>
          {activeFilters > 0 && (
            <button
              className="text-button"
              onClick={() => {
                setKind("all");
                setSource("all");
                setStart("");
                setEnd("");
              }}
            >
              {t("Clear filters", "清除筛选")}
            </button>
          )}
          <ExportLink
            path={`/records.csv?${query}`}
            filename="desk-records.csv"
            onError={setError}
          >
            {t("Export CSV", "导出CSV")}
          </ExportLink>
        </div>
      </div>
      <div id={filterId} className="records-filter-panel" hidden={!filtersOpen}>
        <div className="records-toolbar workspace-record-filters">
          <label>
            {t("Category", "类别")}
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {[
                "all",
                "calendar",
                "tasks",
                "posture",
                "devices",
                "assistant",
              ].map((v, i) => (
                <option key={v} value={v}>
                  {t(
                    [
                      "All",
                      "Calendar",
                      "Tasks",
                      "Posture",
                      "Devices",
                      "Assistant",
                    ][i],
                    ["全部", "日历", "事务", "坐姿", "设备", "助理"][i],
                  )}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("Source", "来源")}
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="all">{t("All sources", "全部来源")}</option>
              <option value="live">{t("Live input", "实时输入")}</option>
              <option value="replay">{t("Replay only", "仅回放")}</option>
            </select>
          </label>
          <label>
            {t("From", "开始")}
            <input
              type="date"
              value={start}
              onInput={(e) => setStart(e.currentTarget.value)}
            />
          </label>
          <label>
            {t("Until", "结束")}
            <input
              type="date"
              value={end}
              onInput={(e) => setEnd(e.currentTarget.value)}
            />
          </label>
        </div>
      </div>
      <p className="footnote">
        {t(
          "Shows up to 300 entries; export includes up to 10,000 matching recent records.",
          "界面最多显示300条，导出包含最近最多10,000条匹配记录。",
        )}
      </p>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      <div className="activity-list" aria-busy={loading}>
        {currentRows.slice(0, 300).map((r) => (
          <div className="activity-row" key={r.sequence}>
            <span className="activity-icon">
              <Circle size={12} />
            </span>
            <div>
              <strong>
                {t(
                  ...(labels[r.action] ?? [
                    r.action.replaceAll("_", " "),
                    "活动：" + r.action,
                  ]),
                )}
              </strong>
              <p>{r.title === "" ? t("Private event", "私人事项") : r.title}</p>
              {typeof r.details.source === "string" && (
                <small
                  className={
                    r.details.source === "replay" ? "source-badge" : ""
                  }
                >
                  {{
                    replay: t("Replay input", "回放输入"),
                    live: t("Live input", "实时输入"),
                    manual: t("Entered by you", "由你录入"),
                    assistant: t(
                      "Assistant draft confirmed",
                      "已确认的助理草稿",
                    ),
                    assistant_confirmed: t(
                      "Assistant draft confirmed",
                      "已确认的助理草稿",
                    ),
                    user_confirmed: t("Confirmed by you", "由你确认"),
                    local_rules: t("Scheduled check-in", "计划检查"),
                    backup: t("Restored from backup", "从备份恢复"),
                  }[r.details.source] ?? t("System record", "系统记录")}
                </small>
              )}
              {typeof r.details.outcome === "string" &&
                outcomes[r.details.outcome] && (
                  <p>{t(...outcomes[r.details.outcome])}</p>
                )}
            </div>
            <time>
              {inZone(r.at, zone)
                .setLocale(locale(language))
                .toFormat("d LLL · HH:mm")}
            </time>
          </div>
        ))}
        {!loading && !error && !currentRows.length && (
          <p className="empty-text">
            {activeFilters
              ? t("No records match these filters.", "没有符合筛选条件的记录。")
              : t(
                  "No activity yet. Saved changes will appear here.",
                  "还没有活动记录，之后保存的更改会显示在这里。",
                )}
          </p>
        )}
      </div>
    </div>
  );
}

export function DeviceView({
  settings,
  language,
  setLanguage,
  onSaved,
  onDeviceLayout,
  onOpenWorkspace,
  t,
}: {
  settings: Settings;
  language: Language;
  setLanguage: (l: Language) => void;
  onSaved: () => void;
  onDeviceLayout: () => void;
  onOpenWorkspace: (
    panel: "posture" | "connections" | "assistant" | "extras" | "data",
  ) => void;
  t: Translate;
}) {
  const workspace = useWorkspace();
  const [zone, setZone] = useState(settings.timezone),
    [hidden, setHidden] = useState(settings.hide_private),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [saved, setSaved] = useState(false);
  const [baseline, setBaseline] = useState(settings);
  const dirty = zone !== baseline.timezone || hidden !== baseline.hide_private;
  useDraftGuard(dirty, busy);
  useEffect(() => {
    if (settings.version > baseline.version && !dirty && !busy) {
      setZone(settings.timezone);
      setHidden(settings.hide_private);
      setBaseline(settings);
    }
  }, [settings.version, baseline.version, dirty, busy]);
  async function save() {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const result = await write<{ settings: Settings }>("/settings", {
        expected_version: baseline.version,
        timezone: zone,
        hide_private: hidden,
      });
      setBaseline(result.settings);
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
          <h1>{t("Settings", "设置")}</h1>
        </div>
      </header>
      <PermissionsPanel t={t} />
      <section className="settings-section">
        <h2>{t("Workspace", "工作空间")}</h2>
        <div className="setting-row">
          <span>
            <strong>{t("Language", "语言")}</strong>
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
          </label>
          <select
            id="timezone"
            value={zone}
            disabled={busy}
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
            disabled={busy}
            onChange={(e) => {
              setHidden(e.target.checked);
              setSaved(false);
            }}
          />
        </div>
        {!!error && <p className="error-message">{errorText(error, t)}</p>}
        {dirty && settings.version !== baseline.version && (
          <p role="alert">
            {t(
              "Preferences changed on another screen. Discard your edits to load the latest values before saving.",
              "另一端已修改偏好。先放弃当前修改以加载最新设置，再重新编辑。",
            )}
          </p>
        )}
        <div className="settings-save">
          <button
            className="primary"
            disabled={busy || !dirty || settings.version !== baseline.version}
            onClick={save}
          >
            {busy ? t("Saving…", "保存中…") : t("Save preferences", "保存偏好")}
          </button>
          {dirty && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => {
                setZone(settings.timezone);
                setHidden(settings.hide_private);
                setBaseline(settings);
                setError(null);
              }}
            >
              {t("Discard changes", "放弃修改")}
            </button>
          )}
          {saved && <span role="status">{t("Saved", "已保存")}</span>}
        </div>
      </section>
      <section className="settings-section">
        <h2>{t("Desk connections", "桌面连接")}</h2>
        <div className="workspace-entry-list">
          <button onClick={() => onOpenWorkspace("data")}>
            <Link2 />
            {t("Import & share", "导入与分享")}
          </button>
          <button onClick={() => onOpenWorkspace("assistant")}>
            <Sparkles />
            {t("Assistant", "助理")}
          </button>
          <button onClick={() => onOpenWorkspace("extras")}>
            <SlidersHorizontal />
            {t("Calendar & companion", "日历与助理")}
          </button>
          <button onClick={() => onOpenWorkspace("posture")}>
            <Camera />
            {t("Posture & feedback", "坐姿与反馈")}
          </button>
          <button onClick={() => onOpenWorkspace("connections")}>
            <Link2 />
            {t("Pairing & outputs", "配对与实体反馈")}
          </button>
        </div>
        {[
          [
            t("Camera & posture", "摄像头与坐姿"),
            postureLabel(workspace.data?.posture, t),
          ],
          [
            t("Voice assistant", "语音助理"),
            workspace.data?.voice.configured
              ? t("Configured", "已配置")
              : t("Not configured", "未配置"),
          ],
          [
            t("Robotic arm", "机械臂"),
            workspace.data?.outputs.connected &&
            workspace.data.outputs.capabilities.includes("arm")
              ? t("Controller connected", "控制器已连接")
              : t("Not connected", "未连接"),
          ],
          [
            t("Weather", "天气"),
            workspace.data?.calendar_extras.weather.status === "current"
              ? t("Current reading", "最新观测")
              : workspace.data?.calendar_extras.weather.status ===
                  "not_configured"
                ? t("Location not selected", "未选择地区")
                : t("Unavailable or stale", "不可用或已过期"),
          ],
          [
            t("External calendars", "外部日历"),
            workspace.data?.google.connected
              ? t("Google connected", "Google已连接")
              : t("Not connected", "未连接"),
          ],
        ].map(([name, state]) => (
          <div className="connection-row" key={name}>
            <span>{name}</span>
            <small>{state}</small>
          </div>
        ))}

        <button className="secondary" onClick={onDeviceLayout}>
          {t("Open device layout", "打开设备布局")}
          <ArrowUpRight size={16} />
        </button>
      </section>
      <section className="settings-section">
        <h2>{t("Connection", "连接")}</h2>
        {isNative && (
          <button
            className="text-button"
            disabled={dirty || busy}
            onClick={() =>
              window.dispatchEvent(new Event("desk:change-server"))
            }
          >
            {t("Change desk address", "更换桌面地址")}
          </button>
        )}
        <div className="setting-row">
          <span>
            <strong>{workspace.data?.principal.name ?? "Owner"}</strong>
            <small>{t("Connected workspace", "已连接工作空间")}</small>
          </span>
        </div>
      </section>
      <PhoneFeatures t={t} />
    </div>
  );
}
