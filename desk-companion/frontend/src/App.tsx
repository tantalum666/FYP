import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DateTime } from "luxon";
import {
  Bell,
  CalendarDays,
  FileText,
  Globe,
  House,
  Brain,
  ListTodo,
  LoaderCircle,
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
import type { Language, Page, Snapshot, Translate, View } from "./types";
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
import { MemoryPanel } from "./workspace/MemoryPanel";
import { PersonaPanel } from "./workspace/PersonaPanel";
import { TaskPanel } from "./workspace/TaskPanel";
import { DataPanel } from "./workspace/DataPanel";
import { PageCompanion } from "./companion/PageCompanion";
import { AssistantPanel } from "./workspace/AssistantPanel";
import { ExtrasPanel } from "./workspace/ExtrasPanel";
import { PosturePanel } from "./workspace/PosturePanel";
import { ConnectionsPanel } from "./workspace/ConnectionsPanel";
import { useCalendarEditor } from "./components/useCalendarEditor";
import { DeviceView, RecordsView, TodayView } from "./components/Views";
import { LoginView } from "./components/LoginView";
import { useWorkspaceSession } from "./useWorkspaceSession";
import { classifyFailure } from "./surfaceStatus";
import { failureNotice, loadingNotice, offlineNotice } from "./surfaceNotice";

const nav = [
  { id: "today", en: "Today", zh: "今天", Icon: House },
  { id: "calendar", en: "Calendar", zh: "日历", Icon: CalendarDays },
  { id: "tasks", en: "Tasks", zh: "事务", Icon: ListTodo },
  { id: "memory", en: "Memory", zh: "记忆", Icon: Brain },
  { id: "persona", en: "Style", zh: "风格", Icon: Sparkles },
  { id: "records", en: "Records", zh: "记录", Icon: FileText },
  { id: "device", en: "Settings", zh: "设置", Icon: SettingsIcon },
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
  const [showReminders, setShowReminders] = useState(false);
  const [filters, setFilters] = useState({ personal: true, study: true });
  const [error, setError] = useState<unknown>(null),
    [recovering, setRecovering] = useState(false);
  const { session, setSession, recoverSession, expired: sessionExpired } = useWorkspaceSession(setError);
  const currentRevision = useRef(0);
  const needsRefresh = useRef(false);
  const [loadedRange, setLoadedRange] = useState("");
  const [scrollHour, setScrollHour] = useState(8);
  const [workspacePanel, setWorkspacePanel] = useState<
    "posture" | "connections" | "extras" | "data" | null
  >(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantTask, setAssistantTask] = useState<{
    id: string;
    title: string;
  }>();
  useEffect(() => {
    if (session === null) {
      setAssistantOpen(false);
      setAssistantTask(undefined);
    }
  }, [session]);
  const [wideWorkspace, setWideWorkspace] = useState(
    () => matchMedia("(min-width: 1200px)").matches,
  );
  const assistantDocked = assistantOpen && wideWorkspace;
  const openAssistant = () => {
    if (!assistantOpen) setAssistantTask(undefined);
    setAssistantOpen(true);
  };
  const discussTask = (id: string, title: string) => {
    if (assistantOpen && assistantTask?.id !== id) {
      setNotice(
        t(
          "Close the current assistant before starting a task discussion.",
          "请先关闭当前助理，再开始这件事务的讨论。",
        ),
      );
      return;
    }
    setAssistantTask({ id, title });
    setAssistantOpen(true);
  };
  useEffect(() => {
    const media = matchMedia("(min-width: 1200px)");
    const update = () => setWideWorkspace(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
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
  const { editor, setEditor, detail, setDetail, newEvent, editEvent } =
    useCalendarEditor({
      selectedDate: page === "today" ? dayISO(today) : anchorDate,
      now,
      zone,
      onError: setError,
    });
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

  function failOwnerRequest(error: unknown) {
    const kind = classifyFailure(error, !!session);
    if (kind === "session-expired" || kind === "signed-out") void recoverSession();
    else if (kind === "error") { setError(error); setConnection("online"); }
    else setConnection("offline");
  }
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
          failOwnerRequest(e);
        }
      });
    return () => {
      active = false;
    };
  }, [session, startISO, endISO, nonce, recoverSession]);
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
          failOwnerRequest(e);
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
  }, [session, refresh, recoverSession]);
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
  async function logout() {
    if (assistantOpen) {
      setNotice(
        t(
          "Close the assistant before signing out.",
          "请先关闭助理，再退出登录。",
        ),
      );
      return;
    }
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
    return loadingNotice(
      t("Opening your workspace…", "正在打开工作空间…"),
      <LoaderCircle className="spinner" aria-hidden="true" />,
    );
  if (session === null)
    return (
      <LoginView
        t={t}
        language={language}
        setLanguage={setLanguage}
        expired={sessionExpired}
        startupError={error}
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
    <div
      className={`app-shell ${deviceLayout ? "device-layout" : ""} ${assistantDocked ? "assistant-docked" : ""}`}
    >
      <aside className="sidebar">
        <div className="app-name">
          Desk
          <br />
          Companion
        </div>
        <div className="sidebar-scroll">
          <nav aria-label={t("Main navigation", "主导航")}>
            {nav.map(({ id, en, zh, Icon }, index) => (
              <div className="sidebar-nav-item" key={id}>
                {(index === 3 || index === 5) && (
                  <p className="sidebar-group-label">
                    {index === 3
                      ? t("Assistant", "助理")
                      : t("Workspace", "工作空间")}
                  </p>
                )}
                <button
                  className={page === id ? "selected" : ""}
                  onClick={() => goPage(id)}
                  aria-current={page === id ? "page" : undefined}
                >
                  <Icon />
                  {id === "memory"
                    ? t("Saved memories", "已保存记忆")
                    : id === "persona"
                      ? t("Assistant style", "助理风格")
                      : t(en, zh)}
                </button>
              </div>
            ))}
          </nav>
          {(page === "today" || page === "calendar") && (
            <details className="sidebar-calendar-tools">
              <summary>{t("Calendar shortcuts", "日历快捷操作")}</summary>
              <MiniMonth
                anchor={DateTime.fromISO(pickerDate, { zone })}
                selected={anchor}
                language={language}
                onSelect={selectDay}
                onMonth={(n) =>
                  setPickerDate(
                    dayISO(
                      DateTime.fromISO(pickerDate, { zone }).plus({
                        months: n,
                      }),
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
            </details>
          )}
        </div>
        <div id="web-companion-home" className="sidebar-companion-home">
          <button className="text-button" onClick={openAssistant}>
            <Sparkles size={16} />
            {t("Chat with assistant", "和助理聊聊")}
          </button>
        </div>
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
        <div className="workspace-topbar">
          <span className={`workspace-connection ${connection}`} role="status">
            <i aria-hidden="true" />
            {connection === "online"
              ? t("Desk connected", "已连接桌面")
              : connection === "offline"
                ? t("Desk offline", "桌面已离线")
                : t("Connecting to desk…", "正在连接桌面…")}
          </span>
          <div className="workspace-topbar-actions">
            <button
              className="assistant-open"
              onClick={openAssistant}
              aria-label={t("Open assistant", "打开助理")}
              aria-expanded={assistantOpen}
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
          </div>
        </div>
        {connection === "offline" && offlineNotice(t("Offline. Showing your last loaded calendar.", "已离线，当前显示上次读取的日历。"), t("Reconnect", "重新连接"), refresh, <RefreshCw size={14} aria-hidden="true" />)}
        {pendingWrite() && !editor && (
          <div className="connection-banner pending" role="status">
            {t("A save is awaiting confirmation.", "有一项保存等待确认。")}
            <button onClick={recover} disabled={recovering}>
              {t("Check save status", "核对保存状态")}
            </button>
          </div>
        )}
        {!!error &&
          failureNotice(errorText(error, t), t("Dismiss", "关闭"), () =>
            setError(null),
          )}
        {!visible ? (
          <div className="app-loading">
            <LoaderCircle className="spinner" />
            <span>{t("Loading your workspace…", "正在读取工作空间…")}</span>
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
                onDiscuss={discussTask}
                onPlan={(event) =>
                  setEditor({ initial: event, scope: "series" })
                }
              />
            )}
            {page === "memory" && (
              <div className="standard-page management-view workspace-panel">
                <MemoryPanel t={t} />
              </div>
            )}
            {page === "persona" && (
              <div className="standard-page management-view workspace-panel">
                <PersonaPanel t={t} />
              </div>
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
                localPreview={session.local_preview}
                onDeviceLayout={() =>
                  window.open(
                    "/?surface=device&page=today",
                    "_blank",
                    "noopener",
                  )
                }
                t={t}
                onOpenWorkspace={(panel) =>
                  panel === "assistant"
                    ? openAssistant()
                    : setWorkspacePanel(panel)
                }
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
          progressive
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
          ) : workspacePanel === "extras" ? (
            <ExtrasPanel t={t} />
          ) : workspacePanel === "data" ? (
            <DataPanel t={t} />
          ) : (
            <ConnectionsPanel t={t} />
          )}
        </Modal>
      )}
      {assistantOpen && (
        <Modal
          title={t("Assistant", "助理")}
          closeLabel={t("Close assistant", "关闭助理")}
          onClose={() => {
            setAssistantOpen(false);
            setAssistantTask(undefined);
          }}
          wide
          docked={assistantDocked}
          className="assistant-dialog"
        >
          <AssistantPanel
            t={t}
            taskId={assistantTask?.id}
            taskTitle={assistantTask?.title}
          />
        </Modal>
      )}
      <PageCompanion
        t={t}
        homeId="web-companion-home"
        blocked={
          !!(
            workspacePanel ||
            editor ||
            detail ||
            showReminders ||
            leavePage ||
            (assistantOpen && !assistantDocked)
          )
        }
        onOpenAssistant={openAssistant}
      />
    </div>
  );
}
