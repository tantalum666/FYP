import { useCallback, useEffect, useRef, useState } from "react";
import {
  ImagePlus,
  MonitorUp,
  Mic,
  MicOff,
  Send,
  Plus,
  MoreHorizontal,
  ArrowLeft,
  Square,
  FolderCheck,
  HelpCircle,
  Box,
} from "lucide-react";
import { errorText, request, write } from "../api";
import type { EventInput, Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { VoiceAudio } from "./audio";
import { useDraftGuard } from "../components/DraftGuard";
import type { Task, TaskInput } from "./taskTypes";
import { apiOrigin } from "../native";
import { DateTime } from "luxon";
import { ComputerJobsPanel } from "./ComputerJobsPanel";
import "./assistant-minimal.css";

interface Proposal {
  id: string;
  kind:
    | "create"
    | "change"
    | "output"
    | "task_create"
    | "task_change"
    | "memory_save"
    | "memory_replace"
    | "memory_delete";
  expires_at: string;
  data: {
    task?: TaskInput;
    original_task?: Task;
    event?: EventInput;
    additional_dates?: string[];
    event_id?: string;
    original?: Pick<
      EventInput,
      | "title"
      | "start_local"
      | "end_local"
      | "timezone"
      | "visibility"
      | "all_day"
    >;
    output?: { kind: string; preset: string };
    body?: string;
    previous?: string;
    change?: {
      action: string;
      scope?: string;
      event?: EventInput;
      task?: TaskInput;
      note?: string;
      minutes?: number;
    };
  };
}
interface Reply {
  mode: string;
  kind: string;
  message: string;
  proposal?: Proposal;
}

export function AssistantPanel({
  t,
  taskId,
}: {
  t: Translate;
  taskId?: string;
}) {
  const { data, refresh, offline, stale } = useWorkspace();
  const [turns, setTurns] = useState<
    Array<{
      id: number;
      role: "user" | "assistant";
      body: string;
      kind?: string;
    }>
  >([]);
  const [view, setView] = useState<"chat" | "jobs" | "help">("chat");
  const [jobsOpened, setJobsOpened] = useState(false);
  const [menu, setMenu] = useState(false);
  const [attachments, setAttachments] = useState(false);
  const [jobAttention, setJobAttention] = useState(0);
  const menuButton = useRef<HTMLButtonElement>(null),
    menuPanel = useRef<HTMLDivElement>(null);
  const owner = useRef(false);
  owner.current = data?.principal.kind === "owner";
  useEffect(() => {
    if (!menu) return;
    menuPanel.current?.querySelector<HTMLElement>("button,a")?.focus();
    const close = (event: PointerEvent) => {
      if (
        !menuPanel.current?.contains(event.target as Node) &&
        !menuButton.current?.contains(event.target as Node)
      )
        setMenu(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [menu]);
  const conversation = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);

  const [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [reply, setReply] = useState<Reply | null>(null),
    [proposals, setProposals] = useState<Proposal[]>([]),
    [notice, setNotice] = useState("");
  const [voiceState, setVoiceState] = useState("idle"),
    [transcript, setTranscript] = useState("");
  const [sharing, setSharing] = useState(false),
    [visionBusy, setVisionBusy] = useState(false),
    [imageCount, setImageCount] = useState(0);
  const imageInput = useRef<HTMLInputElement | null>(null);
  const audio = useRef<VoiceAudio | null>(null),
    alive = useRef(true);
  const speechText = useRef({ user: "", assistant: "" });
  const knownProposals = useRef<Proposal[]>([]);
  const activityReading = useRef(false);
  const loadActivity = useCallback(async () => {
    if (!owner.current || activityReading.current) return;
    activityReading.current = true;
    try {
      const activity = await request<{ jobs: Array<{ state: string }> }>(
        "/computer/jobs",
      );
      if (alive.current)
        setJobAttention(
          activity.jobs.filter(
            (j) => j.state === "review" || j.state === "unknown",
          ).length,
        );
    } catch {
      /* The file view reports its own read failure when opened. */
    } finally {
      activityReading.current = false;
    }
  }, []);
  const language = t("en", "zh");
  const voiceActive = voiceState !== "idle";
  const unavailable = !data || offline || stale;
  const openJobs = () => {
    setJobsOpened(true);
    setView("jobs");
    setMenu(false);
  };
  useEffect(() => {
    conversation.current?.scrollTo({
      top: conversation.current.scrollHeight,
      behavior: "instant",
    });
  }, [turns, proposals, transcript, notice, error, view]);
  function endVoice() {
    const engine = audio.current;
    audio.current = null;
    engine?.close();
    setVoiceState("idle");
    setSharing(false);
    setVisionBusy(false);
    setAttachments(false);
  }
  useEffect(() => {
    if (unavailable) endVoice();
  }, [unavailable]);
  useDraftGuard(!!text.trim(), busy);
  const reload = useCallback(async () => {
    void loadActivity();
    try {
      const next = await request<{ proposals: Proposal[] }>(
        "/assistant/proposals",
      );
      if (alive.current) {
        if (
          knownProposals.current.some(
            (p) =>
              Date.parse(p.expires_at) <= Date.now() &&
              !next.proposals.some((n) => n.id === p.id),
          )
        ) {
          setNotice(
            language === "zh"
              ? "草稿已到期，没有执行任何修改。请重新提出请求。"
              : "The draft expired without making changes. Ask again to prepare a new one.",
          );
        }
        knownProposals.current = next.proposals;
        setProposals(next.proposals);
      }
    } catch (e) {
      if (alive.current) setError(e);
    }
  }, [language, loadActivity]);
  useEffect(() => {
    alive.current = true;
    void reload();
    const timer = setInterval(() => void reload(), 2000);
    return () => {
      alive.current = false;
      clearInterval(timer);
      const engine = audio.current;
      audio.current = null;
      engine?.close();
    };
  }, [reload]);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !text.trim() || voiceActive || unavailable) return;
    const submitted = text;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const result = await write<Reply>("/assistant/messages", {
        message: submitted,
        language,
        task_id: taskId ?? null,
      });
      setReply(result);
      const id = Date.now();
      setTurns((old) =>
        [
          ...old,
          { id, role: "user" as const, body: submitted },
          {
            id: id + 1,
            role: "assistant" as const,
            body: result.message,
            kind: result.kind,
          },
        ].slice(-40),
      );
      setText("");
      void reload();
      window.dispatchEvent(new Event("desk:jobs"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function decide(id: string, action: "confirm" | "cancel") {
    const memoryKind =
      proposals.find((p) => p.id === id)?.kind.startsWith("memory_") ?? false;
    setBusy(true);
    setError(null);
    try {
      const result = await write<{ queued?: boolean; kind?: string }>(
        `/assistant/proposals/${id}/decisions`,
        { action },
      );
      setNotice(
        result.queued
          ? t(
              "Action queued. Check the device receipt for its result.",
              "动作已排队，请在设备回执中查看结果。",
            )
          : action === "confirm"
            ? result.kind?.startsWith("task_")
              ? t(
                  "Task saved. Its progress is kept between conversations.",
                  "事务已保存，进展会在交谈之间保留。",
                )
              : memoryKind
                ? t("Memory updated.", "记忆已更新。")
                : t("Saved to your calendar.", "已保存到日历。")
            : t("Draft cancelled.", "草稿已取消。"),
      );
      await reload();
      await refresh();
      window.dispatchEvent(new Event("desk:calendar"));
      window.dispatchEvent(new Event("desk:tasks"));
    } catch (e) {
      setError(e);
      await reload();
    } finally {
      setBusy(false);
    }
  }
  async function startVoice() {
    if (audio.current || unavailable || !data?.voice.configured || busy) return;
    setError(null);
    setVoiceState("connecting");
    setTranscript("");
    setImageCount(0);
    setSharing(false);
    setVisionBusy(false);
    speechText.current = { user: "", assistant: "" };
    let starting: VoiceAudio | null = null;
    try {
      const engine = new VoiceAudio((event) => {
        if (!alive.current || audio.current !== engine) return;
        if (event.type === "ready") setVoiceState("listening");
        if (event.type === "vision") setSharing(!!event.active);
        if (event.type === "image_sent" && event.count)
          setImageCount(event.count);
        if (event.type === "vision_error")
          setNotice(
            t(
              "Image sharing stopped. Try a smaller image or reconnect.",
              "图像分享已停止，请尝试较小图片或重新连接。",
            ),
          );
        if (event.type === "state" && event.state) setVoiceState(event.state);
        if (event.type === "audio") setVoiceState("speaking");
        if (event.type === "turn_complete" || event.type === "interrupted")
          setVoiceState("listening");
        if (event.type === "interrupted")
          speechText.current = { user: "", assistant: "" };
        if (event.type === "transcript") {
          const role = event.role === "user" ? "user" : "assistant";
          speechText.current[role] = (
            event.final
              ? (event.text ?? "")
              : speechText.current[role] + (event.text ?? "")
          ).slice(-3000);
          setTranscript(
            (speechText.current.user
              ? t("You: ", "你：") + speechText.current.user + "\n"
              : "") +
              (speechText.current.assistant
                ? t("Companion: ", "助理：") + speechText.current.assistant
                : ""),
          );
        }
        if (event.type === "proposal" || event.type === "proposals_changed")
          void reload();
        if (event.type === "jobs_changed")
          window.dispatchEvent(new Event("desk:jobs"));
        if (event.type === "error") {
          audio.current = null;
          engine.close();
          setSharing(false);
          setVisionBusy(false);
          setNotice(
            t(
              "Voice could not continue. Check the connection or provider configuration.",
              "语音未能继续，请检查连接或服务配置。",
            ),
          );
          setVoiceState("idle");
        }
        if (event.type === "closed" || event.type === "ended") {
          audio.current = null;
          setVoiceState("idle");
          setSharing(false);
          setVisionBusy(false);
        }
      });
      starting = engine;
      audio.current = engine;
      const url = new URL("/api/voice/ws", apiOrigin());
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      await engine.start(
        async () =>
          (
            await request<{ ticket: string }>("/voice/tickets", {
              method: "POST",
              body: "{}",
            })
          ).ticket,
        language,
        url.href,
      );
    } catch (e) {
      if (!alive.current || audio.current !== starting) return;
      endVoice();
      setError(e);
      setNotice(
        t(
          "Microphone permission and a configured voice service are required.",
          "需要麦克风权限以及已配置的语音服务。",
        ),
      );
    }
  }
  async function shareVisual(kind: "image" | "screen", file?: File) {
    const engine = audio.current;
    setVisionBusy(true);
    setNotice("");
    try {
      if (kind === "screen") await engine?.shareScreen();
      else if (file) await engine?.shareImage(file);
    } catch {
      if (alive.current && audio.current === engine)
        setNotice(
          t(
            "Sharing did not start. Check permission, image size, and the voice connection.",
            "分享未开始，请检查权限、图片大小和语音连接。",
          ),
        );
    } finally {
      if (alive.current && audio.current === engine) setVisionBusy(false);
    }
  }
  return (
    <div
      className="workspace-panel assistant-panel"
      onKeyDown={(event) => {
        if (event.key === "Escape" && (menu || attachments)) {
          event.preventDefault();
          event.stopPropagation();
          setMenu(false);
          setAttachments(false);
          menuButton.current?.focus();
        }
      }}
    >
      <div className="assistant-toolbar">
        {view !== "chat" && (
          <button
            className="text-button assistant-back"
            onClick={() => {
              setView("chat");
              queueMicrotask(() => composer.current?.focus());
            }}
          >
            <ArrowLeft size={17} />
            {t("Back to chat", "返回对话")}
          </button>
        )}
        <button
          ref={menuButton}
          className="icon-button"
          aria-label={t("More assistant options", "更多助理选项")}
          aria-expanded={menu}
          onClick={() => {
            setMenu(!menu);
            setAttachments(false);
          }}
        >
          <MoreHorizontal size={21} />
        </button>
        {menu && (
          <div
            ref={menuPanel}
            className="assistant-menu"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                setMenu(false);
                menuButton.current?.focus();
              }
            }}
          >
            <button onClick={openJobs}>
              <FolderCheck size={18} />
              {t("File actions & activity", "文件操作与进度")}
            </button>
            <a href="?surface=avatar" target="_blank" rel="noreferrer">
              <Box size={18} />
              {t("Explore A1 in 3D", "查看 A1 的 3D 形象")}
            </a>
            <button
              onClick={() => {
                setView("help");
                setMenu(false);
              }}
            >
              <HelpCircle size={18} />
              {t("What can I ask?", "可以问些什么？")}
            </button>
          </div>
        )}
      </div>
      <section
        className="assistant-chat"
        hidden={view !== "chat"}
        aria-label={t("Conversation", "对话")}
      >
        <div className="assistant-conversation" ref={conversation}>
          {!turns.length &&
            !transcript &&
            !proposals.length &&
            !voiceActive && (
              <div className="assistant-welcome">
                <h3>{t("What can I help you with?", "今天想做些什么？")}</h3>
              </div>
            )}
          {turns.map((turn) => (
            <div className={`assistant-turn ${turn.role}`} key={turn.id}>
              <p>{turn.body}</p>
              {turn.kind === "job" && (
                <button className="text-button" onClick={openJobs}>
                  {t("Review file action", "核对文件操作")}{" "}
                  <ArrowLeft className="arrow-forward" size={15} />
                </button>
              )}
            </div>
          ))}
          {transcript && (
            <p className="assistant-turn voice-transcript" aria-live="polite">
              {transcript}
            </p>
          )}
          {jobAttention > 0 && (
            <button className="assistant-attention" onClick={openJobs}>
              <FolderCheck size={16} />
              {t(
                `${jobAttention} file action(s) need review`,
                `${jobAttention} 项文件操作待核对`,
              )}
            </button>
          )}
          {busy && (
            <p className="assistant-pending" role="status">
              {t("Thinking…", "处理中…")}
            </p>
          )}
          {proposals.map((p) => {
            const event = p.data.event ?? p.data.change?.event;
            const task =
              p.data.task ?? p.data.change?.task ?? p.data.original_task;
            const taskAction = p.data.change?.action ?? "create";
            const taskActionLabel =
              (
                {
                  create: t("Create task", "创建事务"),
                  update: t("Update task details", "更新事务详情"),
                  note: t("Save progress note", "保存进展记录"),
                  complete: t(
                    "Mark complete and stop follow-ups",
                    "标记完成并停止跟进",
                  ),
                  cancel: t(
                    "Cancel task and stop follow-ups",
                    "取消事务并停止跟进",
                  ),
                  reopen: t("Reopen task", "恢复事务"),
                  pause: t("Pause follow-ups", "暂停跟进"),
                  resume: t("Resume follow-ups", "恢复跟进"),
                  snooze: t("Postpone check-in", "延后检查"),
                } as Record<string, string>
              )[taskAction] ?? taskAction;
            const changedTask = p.data.task ?? p.data.change?.task;
            const memoryKind =
              p.kind === "memory_save" ||
              p.kind === "memory_replace" ||
              p.kind === "memory_delete";
            return (
              <article className="assistant-proposal" key={p.id}>
                <span className="workspace-eyebrow">
                  {t("Review before saving", "保存前检查")}
                </span>
                {memoryKind ? (
                  <>
                    <h3>
                      {p.kind === "memory_delete"
                        ? t("Delete a saved fact", "删除一条记忆")
                        : p.kind === "memory_replace"
                          ? t("Correct a saved fact", "更正一条记忆")
                          : t("Save a fact", "保存一条记忆")}
                    </h3>
                    {p.data.previous && (
                      <p>
                        {t("Current: ", "当前：")}
                        {p.data.previous}
                      </p>
                    )}
                    {p.data.body && <blockquote>{p.data.body}</blockquote>}
                    <small>
                      {t(
                        "Nothing is stored until you confirm. A deleted fact is left out of later requests.",
                        "确认前不会写入。删除后，之后的请求不再包含这条事实。",
                      )}
                    </small>
                  </>
                ) : (
                  <>
                    <h3>
                      {task?.title ??
                        event?.title ??
                        (p.kind === "output"
                          ? t("Device feedback", "设备反馈")
                          : t("Change calendar event", "修改日历事项"))}
                    </h3>
                    {task ? (
                      <>
                        <p>
                          <strong>{taskActionLabel}</strong>
                        </p>
                        <p>
                          {t("Deadline: ", "截止：")}
                          {task.due_local?.replace("T", " ") ??
                            t("No deadline", "无截止时间")}{" "}
                          · {task.timezone}
                        </p>
                        {task.next_step && (
                          <p>
                            {t("Next: ", "下一步：")}
                            {task.next_step}
                          </p>
                        )}
                        {task.status === "waiting" && task.waiting_for && (
                          <p>
                            {t("Waiting: ", "等待：")}
                            {task.waiting_for}
                          </p>
                        )}
                        {changedTask && (
                          <>
                            <p>
                              {t("Status: ", "状态：")}
                              {
                                {
                                  todo: t("To do", "待处理"),
                                  in_progress: t("In progress", "进行中"),
                                  waiting: t("Waiting", "等待中"),
                                }[changedTask.status]
                              }
                            </p>
                            {!!changedTask.steps.length && (
                              <ul>
                                {changedTask.steps.map((step, i) => (
                                  <li key={i}>
                                    {step.done ? "✓ " : ""}
                                    {step.title}
                                  </li>
                                ))}
                              </ul>
                            )}
                            <p>
                              {changedTask.follow_up_enabled
                                ? changedTask.check_in_local
                                  ? t("Next check-in: ", "下次检查：") +
                                    changedTask.check_in_local.replace("T", " ")
                                  : t(
                                      `Check in within ${changedTask.interval_minutes} minutes, or at an earlier upcoming deadline.`,
                                      `在${changedTask.interval_minutes}分钟后，或更早的截止时间检查。`,
                                    )
                                : t("Follow-ups off", "跟进未开启")}
                            </p>
                            <p>
                              {changedTask.visibility === "private"
                                ? t("Private task", "私人事务")
                                : t(
                                    "May appear on the desk display",
                                    "可在常亮屏展示",
                                  )}
                            </p>
                            {p.data.original_task?.paused && (
                              <p>
                                {t(
                                  "Follow-ups remain paused until you resume them.",
                                  "跟进会保持暂停，直到你手动恢复。",
                                )}
                              </p>
                            )}
                          </>
                        )}
                        {["snooze", "resume"].includes(taskAction) && (
                          <p>
                            {t("Next check-in: ", "下次检查：")}
                            {DateTime.now()
                              .setZone(task.timezone)
                              .plus({ minutes: p.data.change?.minutes ?? 60 })
                              .toFormat("d LLL HH:mm")}{" "}
                            ({t("from confirmation", "从确认时计算")})
                          </p>
                        )}
                        {p.data.change?.note && (
                          <blockquote>{p.data.change.note}</blockquote>
                        )}
                        {taskAction === "note" && (
                          <p>
                            {t(
                              "This saves your note; it does not change the status or next step.",
                              "这会保存你提供的进展，不会改变状态和下一步。",
                            )}
                          </p>
                        )}
                        <small>
                          {t(
                            "Review saved details in Tasks. This does not reserve calendar time.",
                            "保存后可在事务中编辑详情，不会自动占用日历时间。",
                          )}
                        </small>
                      </>
                    ) : event ? (
                      <>
                        <p>
                          {event.start_local.slice(0, 16).replace("T", " ")} →{" "}
                          {event.end_local.slice(0, 16).replace("T", " ")}
                        </p>
                        <small>
                          {event.timezone} ·{" "}
                          {event.visibility === "private"
                            ? t("Private", "私人")
                            : t("Displayable", "可展示")}
                        </small>
                        {p.data.additional_dates?.length ? (
                          <p>
                            {t("Also on: ", "同时添加：")}
                            {p.data.additional_dates.join(", ")}
                          </p>
                        ) : null}
                        {event.recurrence.frequency !== "none" && (
                          <p>
                            {t("Repeats: ", "重复：")}
                            {event.recurrence.frequency}
                          </p>
                        )}
                      </>
                    ) : (
                      <>
                        {p.data.original && (
                          <>
                            <strong>
                              {p.data.original.title ||
                                t("Private event", "私人事项")}
                            </strong>
                            <p>
                              {p.data.original.start_local.replace("T", " ")} →{" "}
                              {p.data.original.end_local.replace("T", " ")} ·{" "}
                              {p.data.original.timezone}
                            </p>
                          </>
                        )}
                        {p.data.output && (
                          <p>
                            {p.data.output.kind === "arm"
                              ? t("Arm", "机械臂")
                              : t("Light", "灯光")}{" "}
                            · {p.data.output.preset}
                          </p>
                        )}
                        <p>
                          {p.data.change?.action === "delete"
                            ? t("Delete", "删除")
                            : p.data.change?.action === "complete"
                              ? t("Mark complete", "标记完成")
                              : p.data.change?.action === "reopen"
                                ? t("Mark incomplete", "取消完成")
                                : p.data.change
                                  ? t("Update", "更新")
                                  : t("Named preset only", "仅执行预设动作")}
                          {p.data.change &&
                            (p.data.change.scope === "series"
                              ? t(" · Entire series", " · 整个系列")
                              : t(" · This occurrence", " · 仅本次"))}
                        </p>
                      </>
                    )}
                  </>
                )}
                <small>
                  {t("Expires at ", "有效至 ")}
                  {new Date(p.expires_at).toLocaleTimeString(
                    language === "zh" ? "zh-CN" : "en-GB",
                    { hour: "2-digit", minute: "2-digit" },
                  )}
                </small>
                <div className="workspace-inline-actions">
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => void decide(p.id, "confirm")}
                  >
                    {p.kind === "memory_delete"
                      ? t("Confirm deletion", "确认删除")
                      : t("Confirm & save", "确认并保存")}
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => void decide(p.id, "cancel")}
                  >
                    {t("Cancel draft", "取消草稿")}
                  </button>
                </div>
              </article>
            );
          })}

          {notice && (
            <p className="assistant-notice" role="status">
              {notice}
            </p>
          )}
          {!!error && (
            <p className="error-message" role="alert">
              {errorText(error, t)}
            </p>
          )}
          {unavailable && (
            <p className="assistant-notice" role="status">
              {t("Reconnecting to your desk…", "正在重新连接桌面主机…")}
            </p>
          )}
        </div>
        <div className="assistant-input-area">
          {voiceActive ? (
            <div
              className="assistant-call"
              role="group"
              aria-label={t("Voice conversation", "语音对话")}
            >
              <div
                className={`assistant-voice-orb state-${voiceState}`}
                aria-hidden="true"
              >
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <p role="status">
                {voiceState === "connecting"
                  ? t("Connecting…", "正在连接…")
                  : voiceState === "speaking"
                    ? t("Speaking · you can interrupt", "正在说话，可以插话")
                    : voiceState === "thinking"
                      ? t("Thinking…", "正在思考…")
                      : t("Listening…", "正在聆听…")}
              </p>
              <div className="assistant-call-actions">
                {data?.voice.supports_images &&
                  data.principal.kind === "owner" && (
                    <button
                      className="icon-button"
                      aria-label={t(
                        "Share an image or screen",
                        "分享图片或屏幕",
                      )}
                      aria-expanded={attachments}
                      onClick={() => setAttachments(!attachments)}
                    >
                      <Plus size={20} />
                    </button>
                  )}
                <button
                  className="icon-button"
                  aria-label={t("Stop speaking", "停止播报")}
                  onClick={() => audio.current?.interrupt()}
                  disabled={voiceState === "connecting"}
                >
                  <Square size={17} />
                </button>
                <button
                  className="assistant-mic end-call"
                  aria-label={t("End conversation", "结束交谈")}
                  onClick={endVoice}
                >
                  <MicOff size={20} />
                </button>
              </div>
            </div>
          ) : (
            <form className="assistant-composer" onSubmit={send}>
              <textarea
                ref={composer}
                aria-label={t("Message the assistant", "向助理发送消息")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={busy}
                maxLength={3000}
                rows={3}
                placeholder={
                  taskId
                    ? t(
                        "What changed since your last update?",
                        "上次记录后，有什么新进展？",
                      )
                    : t("Ask anything about your day…", "输入你的想法…")
                }
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <div className="assistant-composer-actions">
                <button
                  type="button"
                  className="icon-button"
                  aria-label={t("More actions", "更多操作")}
                  aria-expanded={attachments}
                  onClick={() => setAttachments(!attachments)}
                >
                  <Plus size={21} />
                </button>
                {text.trim() ? (
                  <button
                    className="assistant-mic"
                    disabled={busy || unavailable}
                    aria-label={t("Send message", "发送消息")}
                  >
                    <Send size={20} />
                  </button>
                ) : (
                  <button
                    type="button"
                    className="assistant-mic"
                    disabled={!data?.voice.configured || unavailable || busy}
                    aria-label={t("Start conversation", "开始交谈")}
                    title={
                      !data?.voice.configured
                        ? t("Voice service not configured", "语音服务未配置")
                        : t("Start conversation", "开始交谈")
                    }
                    onClick={() => void startVoice()}
                  >
                    <Mic size={21} />
                  </button>
                )}
              </div>
            </form>
          )}
          {attachments && (
            <div className="assistant-attachments">
              {voiceActive &&
              data?.voice.supports_images &&
              data.principal.kind === "owner" ? (
                <>
                  <p>
                    {t("Send to ", "发送至 ")}
                    {data.voice.provider}.{" "}
                    {t(
                      "Sent images remain in this conversation. No camera opens.",
                      "已发送图片仍保留在本次会话中，不开启摄像头。",
                    )}
                  </p>
                  <div className="workspace-inline-actions">
                    <button
                      className="secondary"
                      disabled={
                        visionBusy || sharing || voiceState === "connecting"
                      }
                      onClick={() => imageInput.current?.click()}
                    >
                      <ImagePlus size={17} />
                      {t("Share an image", "分享一张图片")}
                    </button>
                    {sharing ? (
                      <button
                        className="secondary"
                        onClick={() => audio.current?.stopVision()}
                      >
                        {t("Stop screen sharing", "停止屏幕分享")}
                      </button>
                    ) : (
                      <button
                        className="secondary"
                        disabled={
                          visionBusy ||
                          voiceState === "connecting" ||
                          !navigator.mediaDevices?.getDisplayMedia
                        }
                        onClick={() => void shareVisual("screen")}
                      >
                        <MonitorUp size={17} />
                        {t("Share selected screen", "分享所选屏幕")}
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <button
                    className="text-button"
                    onClick={() => {
                      setText(t("What is on today?", "今天的行程"));
                      setAttachments(false);
                      composer.current?.focus();
                    }}
                  >
                    {t("Today’s briefing", "今日简报")}
                  </button>
                  <button
                    className="text-button"
                    onClick={() => {
                      setAttachments(false);
                      openJobs();
                    }}
                  >
                    {t("File actions & activity", "文件操作与进度")}
                  </button>
                </>
              )}
            </div>
          )}
          <input
            ref={imageInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file && voiceActive) void shareVisual("image", file);
            }}
          />
          {sharing && (
            <div className="assistant-sharing" role="status">
              <span>{t("Screen sharing on", "正在分享屏幕")}</span>
              <button
                className="text-button"
                onClick={() => audio.current?.stopVision()}
              >
                {t("Stop sharing", "停止分享")}
              </button>
            </div>
          )}
          <p className="assistant-caption">
            {voiceActive
              ? t(
                  "Speak naturally. Your mic is on.",
                  "直接交谈，麦克风已开启。",
                )
              : data?.text_ai?.configured
                ? t("Review changes before saving.", "修改会先交给你确认。")
                : t(
                    "Local mode · calendar, tasks & notes",
                    "本地模式 · 日历、事务与笔记",
                  )}
            {imageCount > 0 && (
              <span>
                {" "}
                ·{" "}
                {t(
                  `${imageCount} image frames sent`,
                  `已发送 ${imageCount} 帧图片`,
                )}
              </span>
            )}
          </p>
        </div>
      </section>
      {jobsOpened && (
        <section hidden={view !== "jobs"} className="assistant-secondary">
          <ComputerJobsPanel t={t} taskId={taskId} />
        </section>
      )}
      <section
        hidden={view !== "help"}
        className="assistant-secondary assistant-help"
      >
        <h3>{t("A little help with your day", "帮你理清一天")}</h3>
        <p>
          {t(
            "Ask about today’s calendar, keep track of a task, or prepare a note. Changes wait for your review.",
            "可以查询今天的日程、跟进一件事务，或准备一份笔记。修改会先交给你核对。",
          )}
        </p>
        <ul>
          <li>{t("What is on today?", "今天的行程")}</li>
          <li>{t("Track: finish the project report", "跟进：完成项目报告")}</li>
          <li>
            {t("Remember: I prefer morning meetings", "记住：我喜欢上午开会")}
          </li>
          <li>{t("Save note: project ideas", "保存笔记：项目想法")}</li>
        </ul>
        <p>
          {t(
            "Text and voice can be configured separately. Local mode uses these supported phrases, rather than an open-ended language model. Conversation text is kept only while this panel is open.",
            "文字和语音可分别配置。本地模式使用以上支持的语句；自然对话需要已配置的 AI 服务。对话文字只保留至关闭本面板。",
          )}
        </p>
        {reply?.mode && (
          <small>
            {t("Last reply mode: ", "上次回复模式：")}
            {reply.mode}
          </small>
        )}
      </section>
    </div>
  );
}
