import { citedCalendarOccurrence } from "../workspace/calendarCitation";
import type { ReviewPage } from "../workspace/findingNavigation";
import type { SettingsCategory } from "../components/Views";
import { useDeskInbox } from "../workspace/useDeskInbox";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { DateTime } from "luxon";
import { errorText, pendingWrite, request, retryPending } from "../api";
import { useWorkspaceSession } from "../useWorkspaceSession";
import { usePendingWrite } from "../usePendingWrite";
import { savedEventPosition } from "../dates";
import type { Language, Translate } from "../types";
import { ConnectionView } from "../components/ConnectionView";
import {
  EventDetail,
  EventEditor,
  ReminderDialog,
} from "../components/Dialogs";
import { useCalendarEditor } from "../components/useCalendarEditor";
import { useDraftState } from "../components/DraftGuard";
import { AssistantPanel } from "../workspace/AssistantPanel";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { PhoneHome } from "./PhoneHome";
import { HomeConditions } from "../companion/HomeConditions";
import { AliceAgenda } from "../companion/AliceAgenda";
import { PhoneScreen } from "./PhoneScreen";
import { PhonePlan } from "./PhonePlan";
import {
  PhoneMore,
  PhoneManagement,
  phoneHeadings,
  type PhonePanel,
} from "./PhoneManagement";
import { usePhoneCalendar } from "./usePhoneCalendar";
import { usePhoneEnvironment } from "./usePhoneEnvironment";
import "./phone.css";

export function PhoneApp() {
  const pendingOperation = usePendingWrite();
  const { data, offline, stale, refresh: refreshWorkspace } = useWorkspace();
  const assistantGuard = useDraftState();
  const [language, setLang] = useState<Language>(() =>
    localStorage.getItem("desk.language") === "zh" ? "zh" : "en",
  );
  const t: Translate = useCallback(
    (en, zh) => (language === "en" ? en : zh),
    [language],
  );
  const setLanguage = (value: Language) => {
    localStorage.setItem("desk.language", value);
    setLang(value);
  };
  const [error, setError] = useState<unknown>(null);
  const { session, recoverSession } = useWorkspaceSession(setError);
  const [settingsCategory, setSettingsCategory] =
    useState<SettingsCategory>("general");
  const [trail, setTrail] = useState<PhonePanel[]>([]);
  const panel = trail.at(-1) ?? null;
  const parentPanel = trail.at(-2);
  const setRootPanel = (next: PhonePanel | null) =>
    setTrail(next ? [next] : []);
  const pushPanel = (next: PhonePanel) =>
    setTrail((old) => (old.at(-1) === next ? old : [...old, next]));
  const [planTab, setPlanTab] = useState<"calendar" | "tasks">("calendar");
  const [reminders, setReminders] = useState(false);
  const [selectedTask, selectTask] = useState<string>();
  const [selectedMemory, selectMemory] = useState<string>();
  const [focusedNotice, focusNotice] = useState<string>();
  const calendarRead = useRef(0);
  const [inboxCanNavigate, setInboxCanNavigate] = useState(false);
  const [conversation, setConversation] = useState(false);
  const [task, setTask] = useState<{ id: string; title: string }>();
  const [notice, setNotice] = useState("");
  const [recovering, setRecovering] = useState(false);
  const environment = usePhoneEnvironment();
  const calendar = usePhoneCalendar(
    session,
    environment.now,
    environment.visible,
  );
  const { zone, todayKey, snapshot, homeSnapshot } = calendar;
  const inbox = useDeskInbox(
    !!panel || reminders,
    snapshot?.revision,
    reminders,
    language,
  );
  const {
    editor,
    setEditor,
    detail,
    setDetail,
    newEvent,
    newEventOnDate,
    editEvent,
  } = useCalendarEditor({
    selectedDate: calendar.date,
    now: environment.now,
    zone,
    onError: setError,
  });
  const refresh = () => {
    setError(null);
    calendar.refresh();
    void refreshWorkspace();
  };
  const intentHandled = useRef(false);

  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "zh-Hans";
  }, [language]);
  useEffect(() => {
    const route = (event: Event) => {
      if (
        editor ||
        pendingWrite() ||
        assistantGuard.dirty ||
        assistantGuard.busy ||
        panel
      ) {
        setNotice(t("Finish your current edit first.", "请先完成当前编辑。"));
        return;
      }
      if ((event as CustomEvent).detail === "new") newEventOnDate(todayKey);
      else {
        setPlanTab("calendar");
        calendar.setDate(todayKey);
        setRootPanel("plan");
      }
    };
    window.addEventListener("desk:route", route);
    return () => window.removeEventListener("desk:route", route);
  }, [editor, panel, todayKey, assistantGuard.dirty, assistantGuard.busy, t]);
  useEffect(() => {
    if (!session || intentHandled.current) return;
    const query = new URLSearchParams(location.search);
    if (query.get("action") === "new") {
      intentHandled.current = true;
      newEventOnDate(todayKey);
      query.delete("action");
      history.replaceState(null, "", "?" + query.toString());
    } else if (query.get("page") === "today") {
      intentHandled.current = true;
      setRootPanel("plan");
    }
  }, [session]);
  useEffect(() => {
    if (notice) {
      const timer = setTimeout(() => setNotice(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [notice]);
  const choosePanel = (value: PhonePanel) => {
    setConversation(false);
    setRootPanel(value);
  };
  const showConversation = () => {
    setRootPanel(null);
    setConversation(true);
  };
  const changeDiscussion = (next?: { id: string; title: string }) => {
    if (assistantGuard.dirty || assistantGuard.busy) {
      setNotice(
        t(
          "Finish your message before changing the discussion.",
          "请先处理输入中的消息，再切换讨论。",
        ),
      );
      return;
    }
    setTask(next);
    if (next) showConversation();
  };
  const recover = async () => {
    setRecovering(true);
    try {
      const recoveredChat =
        pendingWrite()?.path === "/assistant/messages/stream";
      await retryPending();
      refresh();
      setNotice(
        recoveredChat
          ? t(
              "Reply recovered. Review any draft before saving.",
              "回复已恢复。草稿仍需核对后确认保存。",
            )
          : t("Save confirmed", "已确认保存"),
      );
    } catch (e) {
      setError(e);
    } finally {
      setRecovering(false);
    }
  };
  useEffect(() => {
    calendarRead.current++;
    const revoke=()=>{calendarRead.current++};
    window.addEventListener("desk:session",revoke);
    return ()=>{revoke();window.removeEventListener("desk:session",revoke);};
  },[session,panel,conversation,assistantGuard.busy,assistantGuard.dirty,data?.personal_context_visible,offline,stale]);
  function reviewPage(target: ReviewPage, id?: string) {
    if (assistantGuard.dirty || assistantGuard.busy || offline || stale) return;
    setReminders(false);
    if (target === "assistant") { focusNotice(id); showConversation(); return; }
    if (target === "memory") { selectMemory(id); pushPanel("memory"); return; }
    if (target === "tasks") { selectTask(id); setPlanTab("tasks"); }
    else { setPlanTab("calendar"); if(target==="today") {calendar.setMonth(false);calendar.setDate(todayKey);} }
    setRootPanel("plan");
  }
  async function openCalendarCitation(ref:string) {
    if (!data?.personal_context_visible || offline || stale || assistantGuard.dirty || assistantGuard.busy) return;
    const read=++calendarRead.current;
    try {
      const found=await citedCalendarOccurrence(ref,zone);
      if(read!==calendarRead.current) return;
      if(!found){setNotice(t("That calendar item is no longer available.","该日程已不可用。"));return;}
      reviewPage("calendar");calendar.setDate(found.day);calendar.setMonth(false);setDetail(found.event);
    } catch (e) {if(read===calendarRead.current)setError(e);}
  }
  const problem = error ?? calendar.error;
  if (session === undefined)
    return (
      <div className="app-loading">
        {t("Opening your workspace…", "正在打开工作空间…")}
      </div>
    );
  if (!session)
    return (
      <>
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
      </>
    );
  return (
    <div
      className={`phone-app alice-home alice-home-phone ${environment.viewport.height < innerHeight - 100 ? "keyboard-open" : ""}`}
      style={
        {
          height: environment.viewport.height,
          top: environment.viewport.top,
          "--phone-viewport-height": `${environment.viewport.height}px`,
        } as CSSProperties
      }
    >
      <PhoneHome
        t={t}
        active={
          environment.visible && !environment.blocked && !conversation && !panel
        }
        motion={environment.motion}
        voiceState={data?.voice.state ?? "idle"}
        listening={!!data?.voice.wake_word?.active}
        obscured={conversation || !!panel}
        connection={
          offline || stale ? "offline" : data ? "online" : "connecting"
        }
        onPlan={() => choosePanel("plan")}
        onMore={() => choosePanel("more")}
        onReconnect={() => void recoverSession()}
      />
      <HomeConditions
        now={environment.now}
        zone={zone}
        language={language}
        t={t}
        visible={!panel && !conversation && environment.visible}
      />
      <AliceAgenda
        monthPreview
        t={t}
        language={language}
        now={environment.now}
        zone={zone}
        events={homeSnapshot?.occurrences ?? null}
        obscured={conversation || !!panel || !!editor || !!detail || reminders}
        onCalendar={() => {
          setPlanTab("calendar");
          calendar.setMonth(true);
          choosePanel("plan");
        }}
        onEvent={setDetail}
        onTasks={() => {
          setPlanTab("tasks");
          choosePanel("plan");
        }}
      />
      <div
        className="phone-chat-layer"
        inert={!!panel || !!editor || !!detail || reminders}
      >
        <AssistantPanel
          t={t}
          immersive
          expanded={conversation}
          onExpandedChange={setConversation}
          suspended={
            !!panel || !!editor || !!detail || reminders || !environment.visible
          }
          taskId={task?.id}
          taskTitle={task?.title}
          onOpenTask={(id)=>reviewPage("tasks",id)} onOpenMemory={(id)=>reviewPage("memory",id)}
          onOpenCalendar={openCalendarCitation} onReviewSurface={reviewPage}
          focusNoticeId={focusedNotice} onFocusNoticeConsumed={()=>focusNotice(undefined)}
          onClearTask={() => changeDiscussion()}
        />
      </div>
      {panel && (
        <PhoneScreen
          key={panel === "plan" ? `plan/${planTab}` : panel}
          t={t}
          title={
            panel === "plan"
              ? planTab === "calendar"
                ? t("Calendar", "日历")
                : t("Tasks", "待办")
              : phoneHeadings(t)[panel]
          }
          onBack={() => setTrail((old) => old.slice(0, -1))}
          backLabel={
            parentPanel
              ? t(
                  `Back to ${phoneHeadings(t)[parentPanel]}`,
                  `返回${phoneHeadings(t)[parentPanel]}`,
                )
              : t("Back to Alice", "返回 Alice")
          }
          currentTab={panel === "plan" ? planTab : "more"}
          onTab={(tab) => {
            if (tab === "more") setRootPanel("more");
            else {
              setPlanTab(tab);
              setRootPanel("plan");
            }
          }}
          onReminders={(canNavigate) => {
            setInboxCanNavigate(canNavigate);
            setReminders(true);
          }}
          notificationCount={
            (snapshot?.reminders.filter((item) => item.status === "due")
              .length ?? 0) + inbox.total
          }
          footer={
            notice ? (
              <p className="phone-panel-notice" role="status">
                {notice}
              </p>
            ) : undefined
          }
        >
          {panel === "plan" ? (
            <PhonePlan
              initialTaskId={selectedTask}
              calendar={calendar}
              t={t}
              language={language}
              offline={offline || stale}
              planTab={planTab}
              onNew={() => newEvent()}
              onOpen={setDetail}
              onPlan={(event) => setEditor({ initial: event, scope: "series" })}
              onDiscuss={(id, title) => changeDiscussion({ id, title })}
            />
          ) : panel === "more" ? (
            <PhoneMore
              t={t}
              language={language}
              setLanguage={setLanguage}
              onNavigate={pushPanel}
              onConversation={showConversation}
            />
          ) : (
            <PhoneManagement
              initialFactId={selectedMemory}
              panel={panel}
              t={t}
              language={language}
              setLanguage={setLanguage}
              settings={snapshot?.settings ?? session.settings}
              settingsCategory={settingsCategory}
              onSettingsCategory={setSettingsCategory}
              revision={snapshot?.revision ?? 0}
              onNavigate={pushPanel}
              onConversation={showConversation}
              onRefresh={refresh}
              onNotice={setNotice}
            />
          )}
          {!!problem && (
            <p className="error-message" role="alert">
              {errorText(problem, t)}
              <button className="text-button" onClick={refresh}>
                {t("Retry", "重试")}
              </button>
            </p>
          )}
          {pendingOperation &&
            pendingOperation.path !== "/assistant/messages/stream" &&
            !editor && (
              <div className="connection-banner">
                <span>
                  {t(
                    "The previous action needs checking.",
                    "上一项操作需要核对。",
                  )}
                </span>
                <button disabled={recovering} onClick={() => void recover()}>
                  {t("Check action status", "核对操作状态")}
                </button>
              </div>
            )}
        </PhoneScreen>
      )}
      {editor && (
        <EventEditor
          state={editor}
          progressive
          t={t}
          onClose={() => setEditor(null)}
          onSaved={(event) => {
            calendar.setDate(savedEventPosition(event, zone).date);
            setEditor(null);
            setPlanTab("calendar");
            setRootPanel("plan");
            calendar.setMonth(false);
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
      {reminders && (
        <ReminderDialog
          onReview={inboxCanNavigate ? reviewPage : undefined}
          inbox={inbox}
          reminders={homeSnapshot?.reminders ?? []}
          language={language}
          zone={zone}
          t={t}
          onClose={() => setReminders(false)}
          onSaved={refresh}
        />
      )}
      {notice && !panel && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
    </div>
  );
}