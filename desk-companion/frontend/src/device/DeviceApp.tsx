import { useCallback, useEffect, useState } from "react";
import { DateTime } from "luxon";
import {
  Bell,
  ListTodo,
  CalendarDays,
  ChevronLeft,
  Plus,
  Settings as SettingsIcon,
  Camera,
  Link2,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";
import {
  ApiError,
  errorText,
  pendingWrite,
  request,
  retryPending,
} from "../api";
import { dayISO, savedEventPosition, viewRange } from "../dates";
import { editable } from "../types";
import type {
  EventInput,
  Language,
  Occurrence,
  Translate,
  View,
} from "../types";
import {
  EventDetail,
  EventEditor,
  ReminderDialog,
} from "../components/Dialogs";
import type { EditorState } from "../components/Dialogs";
import { CalendarToolbar, MonthGrid, TimeGrid } from "../components/Calendar";
import { appearanceAt, displayRange, readAppearance } from "./model";
import type { Appearance } from "./model";
import { useDisplayClock, useIdleDisplay, useScreenAwake } from "./useDisplay";
import { useDeviceCalendar } from "./useDeviceCalendar";
import { DisplayFace } from "./DisplayFace";
import {
  AppearanceChoices,
  DeviceLogin,
  DevicePanel,
  DevicePreferences,
} from "./DevicePanels";
import "./device.css";
import { TaskPanel } from "../workspace/TaskPanel";
import { DataPanel } from "../workspace/DataPanel";
import { AssistantPanel } from "../workspace/AssistantPanel";
import { ExtrasPanel } from "../workspace/ExtrasPanel";
import { useDeskSound } from "./DeskSound";
import { PosturePanel } from "../workspace/PosturePanel";
import { ConnectionsPanel } from "../workspace/ConnectionsPanel";

type Panel =
  | "controls"
  | "calendar"
  | "settings"
  | "login"
  | "posture"
  | "connections"
  | "assistant"
  | "extras"
  | "tasks"
  | "data"
  | null;

export function DeviceApp() {
  const [language, setLanguageState] = useState<Language>(() =>
    localStorage.getItem("desk.device.language.v1") === "zh" ? "zh" : "en",
  );
  const t: Translate = useCallback(
    (en, zh) => (language === "en" ? en : zh),
    [language],
  );
  const setLanguage = (value: Language) => {
    localStorage.setItem("desk.device.language.v1", value);
    setLanguageState(value);
  };
  const [appearance, setAppearanceState] = useState<Appearance>(() =>
    readAppearance(localStorage.getItem("desk.device.appearance.v1")),
  );
  const setAppearance = (value: Appearance) => {
    localStorage.setItem("desk.device.appearance.v1", value);
    setAppearanceState(value);
  };
  const [zone, setZone] = useState(() => {
    const stored =
      localStorage.getItem("desk.device.timezone.v1") ?? "Asia/Hong_Kong";
    return DateTime.now().setZone(stored).isValid ? stored : "Asia/Hong_Kong";
  });
  const clock = useDisplayClock();
  const now = clock.setZone(zone);
  const [panel, setPanel] = useState<Panel>(null);
  const [date, setDate] = useState(() => dayISO(now));
  const [view, setView] = useState<View>("day");
  const [scrollHour, setScrollHour] = useState(8);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [detail, setDetail] = useState<Occurrence | null>(null);
  const [reminders, setReminders] = useState(false);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const anchor = DateTime.fromISO(date, { zone }).startOf("day");
  const range =
    panel === "calendar" ? viewRange(anchor, view) : displayRange(now);
  const workspace = useDeviceCalendar(
    range.start.toUTC().toISO()!,
    range.end.toUTC().toISO()!,
  );
  const { data, session } = workspace;
  const wake = useScreenAwake();
  const sound = useDeskSound(t);
  const theme = appearanceAt(appearance, now.hour);
  const returnDisplay = useCallback(() => {
    setPanel(null);
    setDetail(null);
    setError(null);
  }, []);
  useIdleDisplay(
    !!editor ||
      reminders ||
      settingsDirty ||
      busy ||
      panel === "login" ||
      panel === "posture" ||
      panel === "connections" ||
      panel === "assistant" ||
      panel === "extras" ||
      panel === "data" ||
      panel === "tasks",
    returnDisplay,
  );
  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "zh-Hans";
  }, [language]);
  useEffect(() => {
    const next =
      workspace.snapshot?.settings.timezone ?? session?.settings.timezone;
    if (next && next !== zone) {
      setZone(next);
      localStorage.setItem("desk.device.timezone.v1", next);
    }
  }, [workspace.snapshot?.settings.timezone, session, zone]);
  useEffect(() => {
    if (session === null) {
      setPanel(null);
      setDetail(null);
      setEditor(null);
      setReminders(false);
    }
  }, [session]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  function manage() {
    setPanel(session ? "controls" : "login");
    setError(null);
  }
  function openDay(day: DateTime) {
    if (!session) {
      manage();
      return;
    }
    setDate(dayISO(day));
    setView("day");
    setScrollHour(8);
    setPanel("calendar");
  }
  function openEvent(event: Occurrence) {
    if (session) setDetail(event);
  }
  function addEvent() {
    if (!session) {
      manage();
      return;
    }
    if (pendingWrite()) {
      setError(new ApiError("PENDING_WRITE"));
      setPanel("controls");
      return;
    }
    const base = panel === "calendar" ? anchor : now.startOf("day");
    const start = base.set({
      hour: Math.min(22, Math.max(9, now.hour + 1)),
      minute: 0,
    });
    setEditor({
      scope: "series",
      initial: {
        title: "",
        start_local: start.toFormat("yyyy-MM-dd'T'HH:mm"),
        end_local: start.plus({ hours: 1 }).toFormat("yyyy-MM-dd'T'HH:mm"),
        timezone: zone,
        all_day: false,
        calendar: "personal",
        color: "lavender",
        visibility: "private",
        busy: true,
        location: "",
        notes: "",
        recurrence: { frequency: "none", interval: 1, until: null },
        reminder_minutes: [10],
      },
    });
    if (panel !== "calendar") setPanel(null);
  }
  async function editEvent(scope: "series" | "occurrence") {
    if (!detail) return;
    try {
      const initial =
        scope === "series"
          ? await request<EventInput>(`/events/${detail.id}`)
          : {
              ...editable(detail),
              recurrence: {
                frequency: "none" as const,
                interval: 1,
                until: null,
              },
            };
      setEditor({
        initial,
        id: detail.id,
        version: detail.version,
        occurrenceKey: detail.occurrence_key,
        scope,
        repeating: detail.series_recurrence.frequency !== "none",
      });
      setDetail(null);
    } catch (e) {
      setError(e);
      setDetail(null);
      setPanel("controls");
    }
  }
  async function recover() {
    setBusy(true);
    setError(null);
    try {
      await retryPending();
      setEditor(null);
      workspace.reload();
      setNotice(t("Save confirmed", "已确认保存"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    if (pendingWrite()) {
      setError(new ApiError("PENDING_WRITE"));
      return;
    }
    setBusy(true);
    try {
      await request("/session", { method: "DELETE" });
      workspace.lock();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const mutationError = !!error && (
    <p role="alert" className="error-message">
      {errorText(error, t)}
    </p>
  );
  return (
    <div className={`device-shell ${theme}`}>
      <DisplayFace
        now={now}
        data={data}
        language={language}
        state={workspace.state}
        pending={!!pendingWrite()}
        onManage={manage}
        onEvent={openEvent}
        onDay={openDay}
        onReminders={() => {
          setReminders(true);
        }}
        onRetry={() => void workspace.reconnect()}
        onPosture={() => setPanel("posture")}
        onTasks={() => setPanel("tasks")}
        t={t}
      />
      {panel === "login" && (
        <DevicePanel
          title={t("Connect your calendar", "连接你的日历")}
          onClose={returnDisplay}
          t={t}
        >
          <DeviceLogin
            t={t}
            onLogin={(s) => {
              workspace.setSession(s);
              setPanel(null);
              setError(null);
            }}
          />
        </DevicePanel>
      )}
      {panel === "controls" && session && (
        <DevicePanel
          title={t("Your desk", "桌面控制")}
          onClose={returnDisplay}
          t={t}
        >
          <div className="device-actions">
            <button onClick={() => setPanel("tasks")}>
              <ListTodo />
              <span>{t("Tasks", "事务")}</span>
            </button>
            <button onClick={() => setPanel("data")}>
              <Link2 />
              <span>{t("Import & share", "导入与分享")}</span>
            </button>
            <button onClick={() => setPanel("assistant")}>
              <Sparkles />
              <span>{t("Assistant", "助理")}</span>
            </button>
            <button onClick={() => setPanel("extras")}>
              <SlidersHorizontal />
              <span>{t("Calendar & companion", "日历与助理")}</span>
            </button>
            <button onClick={() => openDay(now.startOf("day"))}>
              <CalendarDays />
              <span>{t("Calendar", "日历")}</span>
            </button>
            <button onClick={addEvent}>
              <Plus />
              <span>{t("Add event", "添加日程")}</span>
            </button>
            <button
              onClick={() => {
                setPanel(null);
                setReminders(true);
              }}
            >
              <Bell />
              <span>{t("Reminders", "提醒")}</span>
            </button>
            <button onClick={() => setPanel("settings")}>
              <SettingsIcon />
              <span>{t("Settings", "设置")}</span>
            </button>
            <button onClick={() => setPanel("posture")}>
              <Camera />
              <span>{t("Posture", "坐姿")}</span>
            </button>
            <button onClick={() => setPanel("connections")}>
              <Link2 />
              <span>{t("Connections", "连接")}</span>
            </button>
          </div>
          <div className="display-options">
            <h3>{t("Display appearance", "显示外观")}</h3>
            <AppearanceChoices
              value={appearance}
              onChange={setAppearance}
              t={t}
            />
            <p>
              {t(
                "Automatic follows your calendar timezone: day from 07:00 to 19:00.",
                "自动模式按日历时区，在07:00至19:00使用日间外观。",
              )}
            </p>
          </div>
          <div className="wake-control">
            <label>
              <input
                type="checkbox"
                checked={sound.enabled}
                onChange={() => void sound.toggle()}
              />
              {t("Enable sound on this screen", "在本屏幕启用声音")}
            </label>
            <small>
              {t(
                "Uses reminder and quiet-hour preferences. Briefings use an available local system voice.",
                "遵循提醒与安静时段设置，简报使用可用的本地系统语音。",
              )}
            </small>
            <label>
              <input
                type="checkbox"
                checked={wake.enabled}
                onChange={wake.toggle}
              />
              {t("Keep this screen awake", "保持本屏幕常亮")}
            </label>
            <small role="status">
              {wake.state === "active"
                ? t(
                    "Active while this display is visible",
                    "本屏幕可见时已启用",
                  )
                : wake.state === "unavailable"
                  ? t(
                      "This browser or system could not keep the screen awake.",
                      "当前浏览器或系统未能保持屏幕唤醒。",
                    )
                  : wake.state === "released"
                    ? t(
                        "Released by the system; resumes when available.",
                        "系统已释放；条件允许时恢复。",
                      )
                    : t(
                        "Off · screen settings remain in control",
                        "未启用 · 遵循屏幕原有设置",
                      )}
            </small>
          </div>
          {pendingWrite() && (
            <div className="device-recovery">
              <p>
                {t(
                  "A save is waiting for confirmation.",
                  "有一项保存等待确认。",
                )}
              </p>
              <button className="primary" disabled={busy} onClick={recover}>
                {t("Retry safely", "安全重试")}
              </button>
            </div>
          )}
          {mutationError}
          <button className="device-return" onClick={returnDisplay}>
            <ChevronLeft />
            {t("Back to display", "返回常亮画面")}
          </button>
        </DevicePanel>
      )}
      {panel === "settings" && session && (
        <DevicePanel
          title={t("Settings", "设置")}
          onClose={returnDisplay}
          t={t}
        >
          {data ? (
            <DevicePreferences
              settings={data.settings}
              language={language}
              setLanguage={setLanguage}
              onSaved={() => {
                workspace.reload();
                setPanel(null);
                setNotice(t("Preferences saved", "偏好已保存"));
              }}
              onDirty={setSettingsDirty}
              onLogout={logout}
              t={t}
            />
          ) : (
            <p>{t("Connecting calendar…", "正在连接日历…")}</p>
          )}
          {mutationError}
        </DevicePanel>
      )}
      {panel === "calendar" && session && (
        <DevicePanel
          title={t("Calendar", "日历")}
          onClose={returnDisplay}
          t={t}
          wide
        >
          <CalendarToolbar
            anchor={anchor}
            view={view}
            setView={setView}
            onNavigate={(n) =>
              setDate(
                dayISO(
                  anchor.plus(
                    view === "month"
                      ? { months: n }
                      : view === "week"
                        ? { weeks: n }
                        : { days: n },
                  ),
                ),
              )
            }
            onToday={() => setDate(dayISO(now))}
            onNew={addEvent}
            language={language}
            zone={zone}
            t={t}
          />
          {data ? (
            view === "month" ? (
              <MonthGrid
                anchor={anchor}
                events={data.occurrences}
                zone={zone}
                language={language}
                onOpen={openEvent}
                onDay={openDay}
                t={t}
              />
            ) : (
              <TimeGrid
                anchor={anchor}
                view={view}
                events={data.occurrences}
                zone={zone}
                language={language}
                onOpen={openEvent}
                onDay={openDay}
                initialHour={scrollHour}
                t={t}
              />
            )
          ) : (
            <div className="device-data-empty">
              <p>
                {workspace.state === "offline"
                  ? t(
                      "Calendar unavailable. Reconnect to load this date.",
                      "日历暂不可用，重新连接后读取此日期。",
                    )
                  : t("Loading your calendar…", "正在读取日历…")}
              </p>
              <button
                className="secondary"
                onClick={() => void workspace.reconnect()}
              >
                {t("Reconnect", "重新连接")}
              </button>
            </div>
          )}
          {mutationError}
          {!!workspace.loadError && workspace.state !== "offline" && (
            <p className="error-message">{errorText(workspace.loadError, t)}</p>
          )}
        </DevicePanel>
      )}
      {session && editor && (
        <EventEditor
          state={editor}
          onClose={() => setEditor(null)}
          onSaved={(event) => {
            const { date, hour } = savedEventPosition(event, zone);
            setEditor(null);
            setDate(date);
            setScrollHour(Math.max(0, hour - 1));
            setPanel("calendar");
            setView("day");
            workspace.reload();
            setNotice(t("Event saved", "日程已保存"));
          }}
          t={t}
        />
      )}
      {session &&
        (panel === "posture" ||
          panel === "connections" ||
          panel === "assistant" ||
          panel === "extras" ||
          panel === "data" ||
          panel === "tasks") && (
          <DevicePanel
            title={
              panel === "tasks"
                ? t("Tasks", "事务")
                : panel === "posture"
                  ? t("Posture & feedback", "坐姿与反馈")
                  : panel === "assistant"
                    ? t("Assistant", "助理")
                    : panel === "extras"
                      ? t("Calendar & companion", "日历与助理")
                      : panel === "data"
                        ? t("Import & share", "导入与分享")
                        : t("Connections", "连接")
            }
            t={t}
            onClose={returnDisplay}
          >
            {panel === "tasks" ? (
              <TaskPanel
                t={t}
                displayMode
                zone={zone}
                onPlan={(event) =>
                  setEditor({ initial: event, scope: "series" })
                }
              />
            ) : panel === "posture" ? (
              <PosturePanel t={t} />
            ) : panel === "assistant" ? (
              <AssistantPanel t={t} />
            ) : panel === "extras" ? (
              <ExtrasPanel t={t} />
            ) : panel === "data" ? (
              <DataPanel t={t} />
            ) : (
              <ConnectionsPanel t={t} isDisplay />
            )}
          </DevicePanel>
        )}
      {session && detail && (
        <EventDetail
          event={detail}
          language={language}
          zone={zone}
          onClose={() => setDetail(null)}
          onEdit={editEvent}
          onChange={() => {
            workspace.reload();
            setNotice(t("Changes saved", "修改已保存"));
          }}
          t={t}
        />
      )}
      {session && reminders && (
        <ReminderDialog
          reminders={workspace.snapshot?.reminders ?? []}
          language={language}
          zone={zone}
          onClose={() => setReminders(false)}
          onSaved={workspace.reload}
          t={t}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
      {sound.notice && (
        <div className="toast" role="status">
          {sound.notice}
        </div>
      )}
    </div>
  );
}
