import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DateTime } from "luxon";
import {
  Bell,
  CalendarDays,
  FileText,
  Globe,
  House,
  ListTodo,
  LoaderCircle,
  Monitor,
  Sparkles,
  RefreshCw,
  Settings as SettingsIcon,
} from "lucide-react";
import {
  ApiError,
  clearPending,
  errorText,
  pendingWrite,
  request,
  retryPending,
} from "./api";
import { dayISO, savedEventPosition, viewRange } from "./dates";
import { editable } from "./types";
import type {
  EventInput,
  Language,
  Occurrence,
  Page,
  Session,
  Snapshot,
  Translate,
  View,
} from "./types";
import {
  CalendarToolbar,
  MiniMonth,
  MonthGrid,
  TimeGrid,
} from "./components/Calendar";
import {
  EventDetail,
  EventEditor,
  ReminderDialog,
  Modal,
} from "./components/Dialogs";
import { useDraftState } from "./components/DraftGuard";
import { TaskPanel } from "./workspace/TaskPanel";
import { DataPanel } from "./workspace/DataPanel";
import { AssistantPanel } from "./workspace/AssistantPanel";
import { ExtrasPanel } from "./workspace/ExtrasPanel";
import { PosturePanel } from "./workspace/PosturePanel";
import { ConnectionsPanel, PairDeviceForm } from "./workspace/ConnectionsPanel";
import type { EditorState } from "./components/Dialogs";
import { DeviceView, RecordsView, TodayView } from "./components/Views";
import { isNative } from "./native";

function LoginView({
  t,
  language,
  setLanguage,
  onLogin,
}: {
  t: Translate;
  language: Language;
  setLanguage: (l: Language) => void;
  onLogin: (s: Session) => void;
}) {
  const [username, setUsername] = useState("owner"),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [pairing, setPairing] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await request("/session", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onLogin(await request<Session>("/session"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-top">
        <strong>Desk Companion</strong>
        <select
          value={language}
          aria-label="Language"
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </div>
      <form className="login-form" onSubmit={submit}>
        <CalendarDays size={34} strokeWidth={1.5} />
        <h1>{t("Your day starts here.", "从容安排每一天。")}</h1>
        <p>
          {t(
            "Sign in to your local desk workspace.",
            "登录你的本地桌面工作空间。",
          )}
        </p>
        <label className="field">
          {t("Username", "账号")}
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="field">
          {t("Password", "密码")}
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {!!error && (
          <p className="error-message" role="alert">
            {errorText(error, t)}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? t("Signing in…", "登录中…") : t("Sign in", "登录")}
        </button>
      </form>
      <button
        className="text-button pair-login-link"
        onClick={() => setPairing(true)}
      >
        {t("Pair with an existing desk", "与已有桌面设备配对")}
      </button>
      {pairing && (
        <>
          <Modal
            title={t("Pair this screen", "配对本终端")}
            closeLabel={t("Close", "关闭")}
            onClose={() => setPairing(false)}
          >
            <PairDeviceForm t={t} onPaired={onLogin} />
          </Modal>
        </>
      )}
      {isNative && (
        <button
          className="text-button pair-login-link"
          onClick={() => window.dispatchEvent(new Event("desk:change-server"))}
        >
          {t("Change desk address", "更换桌面地址")}
        </button>
      )}
    </main>
  );
}

const nav = [
  { id: "today", en: "Today", zh: "今天", Icon: House },
  { id: "calendar", en: "Calendar", zh: "日历", Icon: CalendarDays },
  { id: "tasks", en: "Tasks", zh: "事务", Icon: ListTodo },
  { id: "records", en: "Records", zh: "记录", Icon: FileText },
  { id: "device", en: "Device", zh: "设备", Icon: Monitor },
] as const;

export function App() {
  const draftState = useDraftState();
  const [leavePage, setLeavePage] = useState<Page | null>(null);
  const [language, setLanguageState] = useState<Language>(() =>
    localStorage.getItem("desk.language") === "zh" ? "zh" : "en",
  );
  const t: Translate = useCallback(
    (en, zh) => (language === "en" ? en : zh),
    [language],
  );
  const setLanguage = (l: Language) => {
    localStorage.setItem("desk.language", l);
    setLanguageState(l);
  };
  const query = useMemo(() => new URLSearchParams(location.search), []);
  const [page, setPage] = useState<Page>(() =>
    nav.some((n) => n.id === query.get("page"))
      ? (query.get("page") as Page)
      : "today",
  );
  const [view, setView] = useState<View>(() =>
    ["day", "week", "month"].includes(query.get("view") ?? "")
      ? (query.get("view") as View)
      : innerWidth < 700
        ? "day"
        : "week",
  );
  const deviceLayout = query.get("surface") === "device";
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [connection, setConnection] = useState<"connecting" | "online" | "offline">(
      "connecting",
    );
  const [anchorDate, setAnchorDate] = useState(() =>
    DateTime.fromISO(query.get("date") ?? "").isValid
      ? query.get("date")!
      : DateTime.now().setZone("Asia/Hong_Kong").toISODate()!,
  );
  const [pickerDate, setPickerDate] = useState(anchorDate);
  const [now, setNow] = useState(DateTime.now()),
    [nonce, setNonce] = useState(0),
    [notice, setNotice] = useState("");
  const [editor, setEditor] = useState<EditorState | null>(null),
    [detail, setDetail] = useState<Occurrence | null>(null),
    [showReminders, setShowReminders] = useState(false);
  const [filters, setFilters] = useState({ personal: true, study: true });
  const [error, setError] = useState<unknown>(null),
    [recovering, setRecovering] = useState(false);
  const currentRevision = useRef(0);
  const needsRefresh = useRef(false);
  const [loadedRange, setLoadedRange] = useState("");
  const [scrollHour, setScrollHour] = useState(8);
  const [workspacePanel, setWorkspacePanel] = useState<
    "posture" | "connections" | "assistant" | "extras" | "data" | null
  >(null);
  const zone =
    snapshot?.settings.timezone ??
    session?.settings.timezone ??
    "Asia/Hong_Kong";
  const today = now.setZone(zone).startOf("day");
  const anchor = DateTime.fromISO(
    page === "today" ? dayISO(today) : anchorDate,
    { zone },
  ).startOf("day");
  const range = viewRange(anchor, page === "today" ? "day" : view);
  const startISO = range.start.toUTC().toISO()!,
    endISO = range.end.toUTC().toISO()!;
  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  const intentHandled = useRef(false);
  useEffect(() => {
    if (
      session &&
      snapshot &&
      !pendingWrite() &&
      query.get("action") === "new" &&
      !intentHandled.current
    ) {
      intentHandled.current = true;
      newEvent();
      const next = new URLSearchParams(location.search);
      next.delete("action");
      history.replaceState(null, "", "?" + next.toString());
    }
  }, [session, snapshot]);
  useEffect(() => {
    const route = (event: Event) => {
      if (editor || pendingWrite() || draftState.dirty || draftState.busy) {
        setNotice(t("Finish your current edit first.", "请先完成当前编辑。"));
        return;
      }
      setPage("today");
      if ((event as CustomEvent).detail === "new" && session) newEvent();
    };
    window.addEventListener("desk:route", route);
    return () => window.removeEventListener("desk:route", route);
  }, [editor, session, t, draftState.dirty, draftState.busy]);

  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "zh-Hans";
  }, [language]);
  useEffect(() => {
    const timer = setInterval(() => setNow(DateTime.now()), 15000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let alive = true;
    request<Session>("/session")
      .then((s) => {
        if (alive) setSession(s);
      })
      .catch((e) => {
        if (alive) {
          setSession(null);
          if (!(e instanceof ApiError && e.status === 401)) setError(e);
        }
      });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (!session) return;
    let active = true;
    request<Snapshot>(
      `/calendar?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`,
    )
      .then((s) => {
        if (active) {
          setSnapshot(s);
          currentRevision.current = s.revision;
          setLoadedRange(startISO + "/" + endISO);
          needsRefresh.current = false;
          setConnection("online");
        }
      })
      .catch((e) => {
        if (active) {
          needsRefresh.current = true;
          setConnection("offline");
          if (e instanceof ApiError && e.status === 401) setSession(null);
          else if (e instanceof ApiError && e.status) setError(e);
        }
      });
    return () => {
      active = false;
    };
  }, [session, startISO, endISO, nonce]);
  useEffect(() => {
    if (!session) return;
    let active = true,
      working = false;
    const timer = setInterval(async () => {
      if (working || document.hidden) return;
      working = true;
      try {
        const r = await request<{ revision: number }>("/revision");
        if (active) {
          setConnection("online");
          if (r.revision !== currentRevision.current || needsRefresh.current) {
            needsRefresh.current = false;
            refresh();
          }
        }
      } catch (e) {
        if (active) {
          needsRefresh.current = true;
          setConnection("offline");
          if (e instanceof ApiError && e.status === 401) setSession(null);
        }
      } finally {
        working = false;
      }
    }, 1500);
    const onFocus = () => refresh();
    const onVisible = () => {
      if (!document.hidden) refresh();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [session, refresh]);
  useEffect(() => {
    const p = new URLSearchParams(location.search);
    p.set("page", page);
    p.set("view", view);
    p.set("date", anchorDate);
    history.replaceState(null, "", "?" + p.toString());
  }, [page, view, anchorDate]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4500);
    return () => clearTimeout(timer);
  }, [notice]);

  function goPage(p: Page) {
    if (p === page) return;
    if (draftState.busy) return;
    if (draftState.dirty) {
      setLeavePage(p);
      return;
    }
    setPage(p);
    setError(null);
  }
  function selectDay(d: DateTime) {
    setAnchorDate(dayISO(d));
    setPickerDate(dayISO(d));
    setPage("calendar");
    setView("day");
  }
  function navigate(amount: number) {
    const next = anchor.plus(
      view === "month"
        ? { months: amount }
        : view === "week"
          ? { weeks: amount }
          : { days: amount },
    );
    setAnchorDate(dayISO(next));
    setPickerDate(dayISO(next));
  }
  function newEvent() {
    if (pendingWrite()) {
      setError(new ApiError("PENDING_WRITE"));
      return;
    }
    const day = page === "today" ? today : anchor;
    const start = day.set({
      hour: Math.min(22, Math.max(9, now.setZone(zone).hour + 1)),
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
    }
  }
  async function logout() {
    if (pendingWrite()) {
      setError(new ApiError("PENDING_WRITE"));
      return;
    }
    try {
      await request("/session", { method: "DELETE" });
      clearPending();
      setSnapshot(null);
      setSession(null);
    } catch (e) {
      setError(e);
    }
  }
  async function recover() {
    setRecovering(true);
    setError(null);
    try {
      await retryPending();
      setNotice(t("Save confirmed", "已确认保存"));
      setEditor(null);
      setDetail(null);
      refresh();
    } catch (e) {
      setError(e);
    } finally {
      setRecovering(false);
    }
  }

  if (session === undefined)
    return (
      <div className="app-loading">
        <LoaderCircle className="spinner" />
        <span>{t("Opening your workspace…", "正在打开工作空间…")}</span>
      </div>
    );
  if (session === null)
    return (
      <LoginView
        t={t}
        language={language}
        setLanguage={setLanguage}
        onLogin={(s) => {
          setSession(s);
          setError(null);
          refresh();
        }}
      />
    );
  const visible =
    snapshot && loadedRange === startISO + "/" + endISO
      ? {
          ...snapshot,
          occurrences: snapshot.occurrences.filter((e) => filters[e.calendar]),
        }
      : null;
  const dueCount =
    snapshot?.reminders.filter((r) => r.status === "due").length ?? 0;
  return (
    <div className={`app-shell ${deviceLayout ? "device-layout" : ""}`}>
      <aside className="sidebar">
        <div className="app-name">
          Desk
          <br />
          Companion
        </div>
        <nav aria-label={t("Main navigation", "主导航")}>
          {nav.map(({ id, en, zh, Icon }) => (
            <button
              key={id}
              className={page === id ? "selected" : ""}
              onClick={() => goPage(id)}
              aria-current={page === id ? "page" : undefined}
            >
              <Icon />
              {t(en, zh)}
            </button>
          ))}
        </nav>
        {(page === "today" || page === "calendar") && (
          <>
            <MiniMonth
              anchor={DateTime.fromISO(pickerDate, { zone })}
              selected={anchor}
              language={language}
              onSelect={selectDay}
              onMonth={(n) =>
                setPickerDate(
                  dayISO(
                    DateTime.fromISO(pickerDate, { zone }).plus({ months: n }),
                  ),
                )
              }
            />
            <div className="calendar-filters">
              <h3>{t("Calendars", "日历分类")}</h3>
              {(["personal", "study"] as const).map((c) => (
                <label key={c}>
                  <span className={`filter-dot ${c}`} />
                  <span>
                    {c === "personal"
                      ? t("Personal", "个人")
                      : t("Study", "学习")}
                  </span>
                  <input
                    type="checkbox"
                    checked={filters[c]}
                    onChange={(e) =>
                      setFilters({ ...filters, [c]: e.target.checked })
                    }
                  />
                </label>
              ))}
              {snapshot?.has_samples && (
                <p className="sample-note">
                  {t("Example calendar", "含示例日程")}
                </p>
              )}
            </div>
          </>
        )}
        <footer className="sidebar-footer">
          <label>
            <Globe />
            <select
              aria-label="Language"
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
            >
              <option value="en">English</option>
              <option value="zh">简体中文</option>
            </select>
          </label>
          <button onClick={() => goPage("device")}>
            <SettingsIcon />
            {t("Settings", "设置")}
          </button>
        </footer>
      </aside>
      <div className="mobile-top">
        <strong>Desk Companion</strong>
        <select
          aria-label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">EN</option>
          <option value="zh">中文</option>
        </select>
      </div>
      <main className={`main-content page-${page}`}>
        <button
          className="assistant-open"
          onClick={() => setWorkspacePanel("assistant")}
          aria-label={t("Open assistant", "打开助理")}
        >
          <Sparkles size={18} />
          <span>{t("Assistant", "助理")}</span>
        </button>
        <button
          className={`reminder-button ${dueCount ? "has-due" : ""}`}
          aria-label={t("Open reminders", "打开提醒")}
          onClick={() => setShowReminders(true)}
        >
          <Bell size={19} />
          {dueCount > 0 && <span>{dueCount}</span>}
        </button>
        {connection === "offline" && (
          <div className="connection-banner" role="status">
            {t(
              "Offline. Showing your last loaded calendar.",
              "已离线，当前显示上次读取的日历。",
            )}
            <button onClick={refresh}>
              <RefreshCw size={14} />
              {t("Reconnect", "重新连接")}
            </button>
          </div>
        )}
        {pendingWrite() && !editor && (
          <div className="connection-banner pending" role="status">
            {t("A save is awaiting confirmation.", "有一项保存等待确认。")}
            <button onClick={recover} disabled={recovering}>
              {t("Retry safely", "安全重试")}
            </button>
          </div>
        )}
        {!!error && (
          <div className="global-error" role="alert">
            {errorText(error, t)}
            <button onClick={() => setError(null)}>
              {t("Dismiss", "关闭")}
            </button>
          </div>
        )}
        {!visible ? (
          <div className="app-loading">
            <LoaderCircle className="spinner" />
            <span>{t("Loading your calendar…", "正在读取日历…")}</span>
            {connection === "offline" && (
              <button className="secondary" onClick={refresh}>
                {t("Retry", "重试")}
              </button>
            )}
          </div>
        ) : (
          <>
            {page === "calendar" && (
              <>
                <CalendarToolbar
                  anchor={anchor}
                  view={view}
                  setView={setView}
                  onNavigate={navigate}
                  onToday={() => {
                    setAnchorDate(dayISO(today));
                    setPickerDate(dayISO(today));
                  }}
                  onNew={newEvent}
                  language={language}
                  zone={zone}
                  t={t}
                />
                <div className="calendar-surface">
                  {view === "month" ? (
                    <MonthGrid
                      anchor={anchor}
                      events={visible.occurrences}
                      zone={zone}
                      language={language}
                      onOpen={setDetail}
                      onDay={selectDay}
                      t={t}
                    />
                  ) : (
                    <TimeGrid
                      anchor={anchor}
                      view={view}
                      events={visible.occurrences}
                      zone={zone}
                      language={language}
                      initialHour={scrollHour}
                      onOpen={setDetail}
                      onDay={selectDay}
                      t={t}
                    />
                  )}
                </div>
              </>
            )}
            {page === "today" && (
              <TodayView
                snapshot={visible}
                language={language}
                now={now.setZone(zone)}
                onNew={newEvent}
                onOpen={setDetail}
                onCalendar={() => {
                  setAnchorDate(dayISO(today));
                  goPage("calendar");
                  setView("day");
                }}
                onDevice={() => goPage("device")}
                onTasks={() => goPage("tasks")}
                t={t}
              />
            )}
            {page === "tasks" && (
              <TaskPanel
                t={t}
                zone={zone}
                onPlan={(event) =>
                  setEditor({ initial: event, scope: "series" })
                }
              />
            )}
            {page === "records" && (
              <RecordsView
                revision={visible.revision}
                zone={zone}
                language={language}
                t={t}
              />
            )}
            {page === "device" && (
              <DeviceView
                settings={visible.settings}
                language={language}
                setLanguage={setLanguage}
                onSaved={refresh}
                onLogout={logout}
                onDeviceLayout={() =>
                  window.open(
                    "/?surface=device&page=today",
                    "_blank",
                    "noopener",
                  )
                }
                t={t}
                onOpenWorkspace={setWorkspacePanel}
              />
            )}
          </>
        )}
      </main>
      <nav className="bottom-nav" aria-label={t("Main navigation", "主导航")}>
        {nav.map(({ id, en, zh, Icon }) => (
          <button
            key={id}
            onClick={() => goPage(id)}
            className={page === id ? "selected" : ""}
            aria-current={page === id ? "page" : undefined}
          >
            <Icon />
            {t(en, zh)}
          </button>
        ))}
      </nav>
      {leavePage && (
        <Modal
          title={t("Leave this page?", "离开当前页面？")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setLeavePage(null)}
        >
          <p>
            {t("Your changes have not been saved.", "当前修改还没有保存。")}
          </p>
          <div className="workspace-inline-actions">
            <button className="primary" onClick={() => setLeavePage(null)}>
              {t("Keep editing", "继续编辑")}
            </button>
            <button
              className="secondary"
              onClick={() => {
                setPage(leavePage);
                setLeavePage(null);
              }}
            >
              {t("Discard and leave", "放弃并离开")}
            </button>
          </div>
        </Modal>
      )}
      {editor && (
        <EventEditor
          state={editor}
          t={t}
          onClose={() => setEditor(null)}
          onSaved={(event) => {
            const { date, hour } = savedEventPosition(event, zone);
            setEditor(null);
            setAnchorDate(date);
            setPickerDate(date);
            setPage("calendar");
            setView("day");
            setScrollHour(Math.max(0, hour - 1));
            refresh();
            setNotice(t("Event saved", "日程已保存"));
          }}
        />
      )}
      {detail && (
        <EventDetail
          event={detail}
          language={language}
          zone={zone}
          t={t}
          onClose={() => setDetail(null)}
          onEdit={editEvent}
          onChange={() => {
            refresh();
            setNotice(t("Changes saved", "修改已保存"));
          }}
        />
      )}
      {showReminders && (
        <ReminderDialog
          reminders={snapshot?.reminders ?? []}
          language={language}
          zone={zone}
          t={t}
          onClose={() => setShowReminders(false)}
          onSaved={refresh}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
      {workspacePanel && (
        <Modal
          title={
            workspacePanel === "posture"
              ? t("Posture & feedback", "坐姿与反馈")
              : workspacePanel === "assistant"
                ? t("Assistant", "助理")
                : workspacePanel === "extras"
                  ? t("Calendar & companion", "日历与助理")
                  : workspacePanel === "data"
                    ? t("Import & share", "导入与分享")
                    : t("Connections", "连接")
          }
          closeLabel={t("Close", "关闭")}
          onClose={() => setWorkspacePanel(null)}
          wide
        >
          {workspacePanel === "posture" ? (
            <PosturePanel t={t} />
          ) : workspacePanel === "assistant" ? (
            <AssistantPanel t={t} />
          ) : workspacePanel === "extras" ? (
            <ExtrasPanel t={t} />
          ) : workspacePanel === "data" ? (
            <DataPanel t={t} />
          ) : (
            <ConnectionsPanel t={t} />
          )}
        </Modal>
      )}
    </div>
  );
}
