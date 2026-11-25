import { usePendingWrite } from "./usePendingWrite";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { DateTime } from "luxon";
import {
  Bell,
  Menu,
  ChevronRight,
  PanelLeft,
  ArrowLeft,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";
import {
  ApiError,
  errorText,
  pendingWrite,
  request,
  retryPending,
} from "./api";
import { DiagnosticsPanel } from "./diagnostics.tsx";
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
import { useDeskInbox } from "./workspace/useDeskInbox";
import { WorkspaceNav, destinations as nav } from "./workspace/WorkspaceNav";
import { PersonaPanel } from "./workspace/PersonaPanel";
import { TaskPanel } from "./workspace/TaskPanel";
import { DataPanel } from "./workspace/DataPanel";
import { AliceHome } from "./companion/AliceHome";
import { ExtrasPanel } from "./workspace/ExtrasPanel";
import { PosturePanel } from "./workspace/PosturePanel";
import { ConnectionsPanel } from "./workspace/ConnectionsPanel";
import { useCalendarEditor } from "./components/useCalendarEditor";
import { DeviceView, RecordsView, TodayView } from "./components/Views";
import { ConnectionView } from "./components/ConnectionView";
import { useWorkspaceSession } from "./useWorkspaceSession";
import { classifyFailure } from "./surfaceStatus";
import { failureNotice, loadingNotice, offlineNotice } from "./surfaceNotice";

const desktopRail = window.matchMedia("(min-width: 960px)");
function watchDesktopRail(notify: () => void) {
  desktopRail.addEventListener("change", notify);
  return () => desktopRail.removeEventListener("change", notify);
}

export function App() {
  const pendingOperation = usePendingWrite();
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
      : "assistant",
  );
  const [view, setView] = useState<View>(() =>
    ["day", "week", "month"].includes(query.get("view") ?? "")
      ? (query.get("view") as View)
      : innerWidth < 700
        ? "day"
        : "week",
  );
  const deviceLayout = query.get("surface") === "device";
  const pages = nav.filter(
    (item) => item.id !== "diagnostics" || !deviceLayout,
  );
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
  const { session, recoverSession } = useWorkspaceSession(setError);
  const currentRevision = useRef(0);
  const needsRefresh = useRef(false);
  const [loadedRange, setLoadedRange] = useState("");
  const [scrollHour, setScrollHour] = useState(8);
  const [workspacePanel, setWorkspacePanel] = useState<
    "posture" | "connections" | "extras" | "data" | null
  >(() => query.get("settings") === "connections" ? "connections" : query.get("settings") === "reminders" ? "extras" : null);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const wide = useSyncExternalStore(
    watchDesktopRail,
    () => desktopRail.matches,
  );
  const pinned = wide && page !== "assistant";
  const [railCollapsed, setRailCollapsed] = useState(
    () => localStorage.getItem("desk.sidebar") === "compact",
  );
  function toggleRail() {
    const next = !railCollapsed;
    setRailCollapsed(next);
    localStorage.setItem("desk.sidebar", next ? "compact" : "full");
  }
  const drawer = navigationOpen && !pinned;
  const destination = nav.find((item) => item.id === page)!;
  const inbox = useDeskInbox(
    page !== "assistant" || showReminders,
    snapshot?.revision,
    showReminders || page === "inbox",
    language,
  );
  useEffect(() => {
    if (pinned) setNavigationOpen(false);
  }, [pinned]);
  const [taskToOpen, setTaskToOpen] = useState<string>();
  const [memoryToOpen, setMemoryToOpen] = useState<string>();
  const [chatState, setChatState] = useState({ dirty: false, busy: false });
  const [assistantTask, setAssistantTask] = useState<{
    id: string;
    title: string;
  }>();
  useEffect(() => {
    if (session === null) setAssistantTask(undefined);
  }, [session]);
  const [conversationRequest, requestConversation] = useState(0);
  const openAssistant = () => goPage("assistant");
  function reviewNotice(target: "assistant" | "memory" | "tasks") {
    setShowReminders(false);
    goPage(target);
    if (target === "assistant") requestConversation((n) => n + 1);
  }
  const discussTask = (id: string, title: string) => {
    if (chatState.busy) {
      setNotice(
        t("Wait for the current reply first.", "请先等待当前回复结束。"),
      );
      return;
    }
    setAssistantTask({ id, title });
    goPage("assistant");
  };
  const zone =
    snapshot?.settings.timezone ??
    session?.settings.timezone ??
    "Asia/Hong_Kong";
  const today = now.setZone(zone).startOf("day");
  const anchor = DateTime.fromISO(
    page === "today" || page === "assistant" ? dayISO(today) : anchorDate,
    { zone },
  ).startOf("day");
  const range = viewRange(
    anchor,
    page === "today" || page === "assistant" ? "day" : view,
  );
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
    if (kind === "session-expired" || kind === "signed-out")
      void recoverSession();
    else if (kind === "error") {
      setError(error);
      setConnection("online");
    } else setConnection("offline");
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

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [page]);

  function closeNavigation() {
    setNavigationOpen(false);
    requestAnimationFrame(() => {
      const trigger =
        page === "assistant"
          ? ".alice-home:not([hidden]) .alice-more-button"
          : ".workspace-menu-toggle";
      document.querySelector<HTMLButtonElement>(trigger)?.focus();
    });
  }
  function goPage(p: Page, itemId?: string) {
    if (p === page) {
      closeNavigation();
      return;
    }
    if (draftState.busy) return;
    if (draftState.dirty) {
      setLeavePage(p);
      return;
    }
    setTaskToOpen(p === "tasks" ? itemId : undefined);
    setMemoryToOpen(p === "memory" ? itemId : undefined);
    setPage(p);
    if (navigationOpen) closeNavigation();
    setError(null);
  }
  /** Open Event details for a local calendar:{id}:{occurrence_key} citation. */
  async function openCitedCalendar(ref: string) {
    if (ref.startsWith("calendar:google:") || !ref.startsWith("calendar:")) return;
    if (draftState.busy || chatState.busy) {
      setNotice(
        t("Wait for the current reply first.", "请先等待当前回复结束。"),
      );
      return;
    }
    if (draftState.dirty) {
      setNotice(t("Finish your current edit first.", "请先完成当前编辑。"));
      return;
    }
    const rest = ref.slice("calendar:".length);
    const cut = rest.indexOf(":");
    if (cut <= 0) return;
    const eventId = rest.slice(0, cut);
    const occurrenceKey = rest.slice(cut + 1);
    const day = occurrenceKey.slice(0, 10);
    const dayStart = DateTime.fromISO(day, { zone });
    if (!dayStart.isValid) {
      setNotice(
        t("That calendar item is no longer available.", "该日程已不可用。"),
      );
      return;
    }
    try {
      const start = dayStart.startOf("day").toUTC().toISO()!;
      const end = dayStart.plus({ days: 1 }).startOf("day").toUTC().toISO()!;
      const snap = await request<Snapshot>(
        `/calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      );
      const match = snap.occurrences.find(
        (item) =>
          item.id === eventId && item.occurrence_key === occurrenceKey,
      );
      if (!match) {
        setNotice(
          t("That calendar item is no longer available.", "该日程已不可用。"),
        );
        return;
      }
      setAnchorDate(day);
      setPickerDate(day);
      setPage("calendar");
      setView("day");
      setSnapshot(snap);
      setLoadedRange(start + "/" + end);
      currentRevision.current = snap.revision;
      setDetail(match);
      if (navigationOpen) closeNavigation();
      setError(null);
    } catch (reason) {
      failOwnerRequest(reason);
    }
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
  async function recover() {
    setRecovering(true);
    setError(null);
    try {
      const recoveredChat =
        pendingWrite()?.path === "/assistant/messages/stream";
      await retryPending();
      setNotice(
        recoveredChat
          ? t(
              "Reply recovered. Review any draft before saving.",
              "回复已恢复。草稿仍需核对后确认保存。",
            )
          : t("Save confirmed", "已确认保存"),
      );
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
      <ConnectionView
        t={t}
        language={language}
        setLanguage={setLanguage}
        error={error}
        onReconnect={async () => {
          setError(null);
          await recoverSession();
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
      className={`app-shell conversation-shell ${page === "assistant" ? "home-open" : "desk-workspace"} ${deviceLayout ? "device-layout" : ""} ${navigationOpen ? "navigation-open" : ""} ${pinned && railCollapsed ? "rail-compact" : ""}`}
      onKeyDown={(event) => {
        if (
          navigationOpen &&
          event.key === "Escape" &&
          !event.defaultPrevented
        ) {
          event.preventDefault();
          closeNavigation();
        }
      }}
    >
      <WorkspaceNav
        page={page}
        visible={pinned || drawer}
        drawer={drawer}
        collapsed={railCollapsed}
        onCollapse={toggleRail}
        connection={connection}
        count={dueCount + inbox.total}
        showDiagnostics={!deviceLayout}
        language={language}
        onLanguage={setLanguage}
        onPage={goPage}
        onClose={closeNavigation}
        t={t}
      >
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
      </WorkspaceNav>
      <main className={`main-content page-${page}`} inert={drawer}>
        <div className="workspace-topbar">
          <div className="workspace-topbar-title">
            <button
              className="icon-button workspace-menu-toggle"
              aria-label={t("Navigation", "导航")}
              aria-expanded={drawer}
              aria-controls="workspace-navigation"
              onClick={() => {
                if (navigationOpen) closeNavigation();
                else {
                  setNavigationOpen(true);
                  requestAnimationFrame(() =>
                    document
                      .querySelector<HTMLButtonElement>(".sidebar nav button")
                      ?.focus(),
                  );
                }
              }}
            >
              <Menu size={20} />
            </button>
            {page !== "assistant" && (
              <button
                className="workspace-home-link"
                onClick={openAssistant}
                aria-label={t("Open assistant", "打开助理")}
              >
                <ArrowLeft size={15} />
                Alice
              </button>
            )}
            {page === "assistant" ? (
              <h1>Alice</h1>
            ) : (
              <div className="workspace-crumb">
                <PanelLeft size={16} />
                <span>{t("Workspace", "工作空间")}</span>
                <ChevronRight size={13} />
                <strong>{t(destination.en, destination.zh)}</strong>
              </div>
            )}
          </div>
          <div className="workspace-topbar-actions">
            <span
              className={`workspace-connection ${connection}`}
              role="status"
            >
              <i aria-hidden="true" />
              {connection === "online"
                ? t("Desk connected", "已连接桌面")
                : connection === "offline"
                  ? t("Desk offline", "桌面已离线")
                  : t("Connecting to desk…", "正在连接桌面…")}
            </span>
            <button
              className={`reminder-button ${dueCount + inbox.total ? "has-due" : ""}`}
              aria-label={t("Open reminders", "打开提醒")}
              title={t("Reminders and updates", "提醒与动态")}
              onClick={() =>
                page === "assistant" ? setShowReminders(true) : goPage("inbox")
              }
            >
              <Bell size={19} />
              {dueCount + inbox.total > 0 && (
                <span>{dueCount + inbox.total}</span>
              )}
            </button>
          </div>
        </div>
        {connection === "offline" &&
          offlineNotice(
            t(
              "Offline. Showing your last loaded calendar.",
              "已离线，当前显示上次读取的日历。",
            ),
            t("Reconnect", "重新连接"),
            refresh,
            <RefreshCw size={14} aria-hidden="true" />,
          )}
        {pendingOperation &&
          pendingOperation.path !== "/assistant/messages/stream" &&
          !editor && (
            <div className="connection-banner pending" role="status">
              {t("The previous action needs checking.", "上一项操作需要核对。")}
              <button onClick={recover} disabled={recovering}>
                {t("Check action status", "核对操作状态")}
              </button>
            </div>
          )}
        {!!error &&
          failureNotice(errorText(error, t), t("Dismiss", "关闭"), () =>
            setError(null),
          )}
        <AliceHome
          surface="web"
          conversationRequest={conversationRequest}
          t={t}
          language={language}
          now={now}
          zone={zone}
          events={visible?.occurrences ?? null}
          connection={connection}
          visible={page === "assistant"}
          obscured={
            !!(
              workspacePanel ||
              editor ||
              detail ||
              showReminders ||
              leavePage ||
              navigationOpen
            )
          }
          onPlan={() => {
            selectDay(today);
          }}
          onMore={() => {
            setNavigationOpen(true);
            requestAnimationFrame(() =>
              document
                .querySelector<HTMLButtonElement>(".sidebar nav button")
                ?.focus(),
            );
          }}
          onReconnect={() => {
            refresh();
            void recoverSession();
          }}
          onTasks={() => goPage("tasks")}
          onEvent={setDetail}
          task={assistantTask}
          onClearTask={() => setAssistantTask(undefined)}
          onOpenTask={(id) => goPage("tasks", id)}
          onConversationState={setChatState}
        />
        {page !== "assistant" &&
          (!visible ? (
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
                <>
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
                    onTasks={(id) => goPage("tasks", id)}
                    t={t}
                  />
                </>
              )}
              {page === "inbox" && (
                <ReminderDialog
                  inline
                  onReview={reviewNotice}
                  reminders={visible.reminders}
                  inbox={inbox}
                  language={language}
                  zone={zone}
                  t={t}
                  onClose={openAssistant}
                  onSaved={refresh}
                />
              )}
              {page === "tasks" && (
                <>
                  <TaskPanel
                    initialTaskId={taskToOpen}
                    t={t}
                    zone={zone}
                    onDiscuss={discussTask}
                    onPlan={(event) =>
                      setEditor({ initial: event, scope: "series" })
                    }
                  />
                </>
              )}
              {page === "memory" && (
                <div className="standard-page management-view workspace-panel">
                  <MemoryPanel t={t} initialFactId={memoryToOpen} />
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
              {page === "diagnostics" && (
                <DiagnosticsPanel t={t} language={language} />
              )}
            </>
          ))}
      </main>
      {drawer && (
        <button
          className="workspace-nav-scrim"
          tabIndex={-1}
          aria-label={t("Close navigation", "关闭导航")}
          onClick={closeNavigation}
        />
      )}
      <nav
        className="bottom-nav"
        inert={drawer}
        aria-label={t("Main navigation", "主导航")}
      >
        {pages
          .filter(({ id }) =>
            ["today", "tasks", "calendar", "inbox"].includes(id),
          )
          .map(({ id, en, zh, Icon }) => (
            <button
              key={id}
              aria-label={t(en, zh)}
              onClick={() => goPage(id)}
              className={page === id ? "selected" : ""}
              aria-current={page === id ? "page" : undefined}
            >
              <span className="dock-icon">
                <Icon />
                {id === "inbox" && dueCount + inbox.total > 0 && (
                  <small>{dueCount + inbox.total}</small>
                )}
              </span>
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
                setTaskToOpen(undefined);
                setPage(leavePage);
                setNavigationOpen(false);
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
          onReview={reviewNotice}
          inbox={inbox}
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
    </div>
  );
}
