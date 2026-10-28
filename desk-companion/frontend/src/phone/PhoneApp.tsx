import { useCallback, useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { errorText, pendingWrite, request, retryPending } from "../api";
import { useWorkspaceSession } from "../useWorkspaceSession";
import { savedEventPosition } from "../dates";
import type { Language, Translate } from "../types";
import { LoginView } from "../components/LoginView";
import {
  EventDetail,
  EventEditor,
  Modal,
  ReminderDialog,
} from "../components/Dialogs";
import { useCalendarEditor } from "../components/useCalendarEditor";
import { useDraftState } from "../components/DraftGuard";
import { AssistantPanel } from "../workspace/AssistantPanel";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { PhoneHome, UpcomingHint } from "./PhoneHome";
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
  const {
    session,
    setSession,
    expired: sessionExpired,
  } = useWorkspaceSession(setError);
  const [panel, setPanel] = useState<PhonePanel | null>(null);
  const [planTab, setPlanTab] = useState<"calendar" | "tasks">("calendar");
  const [reminders, setReminders] = useState(false);
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
        setPanel("plan");
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
      setPanel("plan");
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
    setPanel(value);
  };
  const showConversation = () => {
    setPanel(null);
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
  const logout = async () => {
    if (assistantGuard.dirty || assistantGuard.busy || pendingWrite()) {
      setNotice(t("Finish your current edit first.", "请先完成当前编辑。"));
      return;
    }
    try {
      await request("/session", { method: "DELETE" });
      setSession(null);
      setTask(undefined);
      setPanel(null);
    } catch (e) {
      setError(e);
    }
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
        <LoginView
          t={t}
          language={language}
          setLanguage={setLanguage}
          expired={sessionExpired}
          startupError={error}
          onLogin={(value) => {
            setSession(value);
            setError(null);
          }}
        />
      </>
    );
  return (
    <div
      className={`phone-app ${environment.viewport.height < innerHeight - 100 ? "keyboard-open" : ""}`}
      style={{
        height: environment.viewport.height,
        top: environment.viewport.top,
      }}
    >
      <PhoneHome
        t={t}
        active={environment.visible && !environment.blocked && !conversation}
        motion={environment.motion}
        voiceState={data?.voice.state ?? "idle"}
        obscured={conversation || !!panel}
        connection={
          offline || stale ? "offline" : data ? "online" : "connecting"
        }
        onPlan={() => choosePanel("plan")}
        onMore={() => choosePanel("more")}
      />
      <div className="phone-chat-layer" inert={!!panel || environment.blocked}>
        <AssistantPanel
          t={t}
          immersive
          expanded={conversation}
          onExpandedChange={setConversation}
          suspended={!!panel || environment.blocked || !environment.visible}
          homeHint={
            <UpcomingHint
              next={calendar.next}
              today={calendar.today}
              zone={zone}
              language={language}
              t={t}
              onOpen={(event) => {
                calendar.setDate(
                  DateTime.fromISO(event.start).setZone(zone).toISODate()!,
                );
                setDetail(event);
              }}
            />
          }
          taskId={task?.id}
          taskTitle={task?.title}
          onClearTask={() => changeDiscussion()}
        />
      </div>
      {panel && (
        <Modal
          title={phoneHeadings(t)[panel]}
          onClose={() => setPanel(null)}
          closeLabel={t("Back to Alice", "返回 Alice")}
          className="phone-sheet"
          footer={
            notice ? (
              <p className="phone-panel-notice" role="status">
                {notice}
              </p>
            ) : undefined
          }
          wide
        >
          {panel === "plan" ? (
            <PhonePlan
              calendar={calendar}
              t={t}
              language={language}
              offline={offline || stale}
              planTab={planTab}
              setPlanTab={setPlanTab}
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
              onNavigate={setPanel}
              onConversation={showConversation}
              onReminders={() => setReminders(true)}
            />
          ) : (
            <PhoneManagement
              panel={panel}
              t={t}
              language={language}
              setLanguage={setLanguage}
              settings={snapshot?.settings ?? session.settings}
              revision={snapshot?.revision ?? 0}
              session={session}
              onNavigate={setPanel}
              onConversation={showConversation}
              onRefresh={refresh}
              onLogout={() => void logout()}
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
          {pendingWrite() && !editor && (
            <div className="connection-banner">
              <span>
                {t("A save is awaiting confirmation.", "有一项保存等待确认。")}
              </span>
              <button disabled={recovering} onClick={() => void recover()}>
                {t("Check save status", "核对保存状态")}
              </button>
            </div>
          )}
        </Modal>
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
            setPanel("plan");
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
