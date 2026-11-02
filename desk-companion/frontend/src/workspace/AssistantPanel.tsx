import type { ReactNode } from "react";
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
  Camera,
  SquarePen,
} from "lucide-react";
import {
  ApiError,
  errorText,
  pendingWrite,
  request,
  retryPending,
  write,
  writeStream,
} from "../api";
import { progressLabel, type ToolProgress } from "../replyStream";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { VoiceAudio } from "./audio";
import { handoverTicket } from "./voice-ticket";
import type { TurnMeasurement } from "./voice-timing";
import { useDraftGuard } from "../components/DraftGuard";
import { apiOrigin } from "../native";
import { ProposalActionCard } from "./ProposalActionCard";
import type { Proposal, Reply } from "./assistantTypes";
import { JobActionCard } from "./JobActionCard";
import { requestJobAction } from "./jobRequests";
import type { JobAction } from "./jobRequests";
import {
  isApplicationAction,
  isDesktopAction,
  isFolderAction,
  jobStateLabel,
} from "./jobTypes";
import type { ComputerJob } from "./jobTypes";
import { PermissionControl } from "./PermissionsPanel";
import { ComputerJobsPanel } from "./ComputerJobsPanel";
import "./assistant-minimal.css";
import { useVoiceWorkHandoff } from "./voiceWork/useVoiceWorkHandoff";
import { ToolActivity, type ToolCall } from "./ToolActivity";
import { MediaDevicePanel } from "./media/MediaDevicePanel";

export function AssistantPanel({
  t,
  taskId,
  taskTitle,
  immersive = false,
  workspace = false,
  onStateChange,
  expanded = false,
  onExpandedChange,
  suspended = false,
  homeHint,
  onClearTask,
}: {
  t: Translate;
  taskId?: string;
  taskTitle?: string;
  immersive?: boolean;
  workspace?: boolean;
  onStateChange?: (state: { dirty: boolean; busy: boolean }) => void;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  suspended?: boolean;
  homeHint?: ReactNode;
  onClearTask?: () => void;
}) {
  const { data, refresh, offline, stale } = useWorkspace();
  const [turns, setTurns] = useState<
    Array<{
      id: number;
      role: "user" | "assistant";
      body: string;
      kind?: string;
      jobId?: string;
    }>
  >([]);
  const [view, setView] = useState<
    "chat" | "jobs" | "help" | "timing" | "activity"
  >("chat");
  const [jobsOpened, setJobsOpened] = useState(false);
  const [voiceSlow, setVoiceSlow] = useState(false);
  const [voiceTimings, setVoiceTimings] = useState<TurnMeasurement[]>([]);
  const [menu, setMenu] = useState(false);
  const [attachments, setAttachments] = useState(false);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [jobs, setJobs] = useState<ComputerJob[]>([]);
  const [jobsError, setJobsError] = useState<unknown>(null);
  const [jobActionError, setJobActionError] = useState<unknown>(null);
  const [jobActionNotice, setJobActionNotice] = useState("");
  const [jobsReadAt, setJobsReadAt] = useState(0);
  const seenJobs = useRef<Set<string> | null>(null);
  const [attentionJobs, setAttentionJobs] = useState<string[]>([]);
  const [jobBusy, setJobBusy] = useState<string | null>(null);
  const [jobCancelling, setJobCancelling] = useState<string | null>(null);
  const jobScope = useRef(taskId);
  jobScope.current = taskId;
  const jobAttention = jobs.filter(
    (job) => job.state === "review" || job.state === "unknown",
  ).length;
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
  const followLatest = useRef(true);
  const jobRevision = jobs.map((job) => `${job.id}:${job.version}`).join(",");
  const composer = useRef<HTMLTextAreaElement>(null);

  const [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const pendingJob = pendingWrite()?.path.startsWith("/computer/")
    ? pendingWrite()
    : null;
  const [reply, setReply] = useState<Reply | null>(null),
    [liveMessage, setLiveMessage] = useState(""),
    [progress, setProgress] = useState<ToolProgress[]>([]),
    [proposals, setProposals] = useState<Proposal[]>([]),
    [calls, setCalls] = useState<ToolCall[] | null>(null),
    [notice, setNotice] = useState("");
  const [voiceState, setVoiceState] = useState("idle"),
    [transcript, setTranscript] = useState("");
  useEffect(() => {
    const field = composer.current;
    if (!field) return;
    field.style.height = "44px";
    field.style.height = `${Math.min(132, field.scrollHeight)}px`;
  }, [text, view, voiceState]);
  const [sharing, setSharing] = useState(false),
    [visionBusy, setVisionBusy] = useState(false),
    [imageCount, setImageCount] = useState(0);
  const imageInput = useRef<HTMLInputElement | null>(null);
  const audio = useRef<VoiceAudio | null>(null),
    alive = useRef(true);
  const conversationId = useRef<string | undefined>(undefined);
  const pendingSubmission = useRef<string | null>(null);
  const submissionGeneration = useRef(0);
  const pendingHttp = useRef<{
    body: object;
    generation: number;
    message: string;
  } | null>(null);
  const modeSwitching = useRef(false);
  const [microphone, setMicrophone] = useState(false);
  useEffect(() => {
    onStateChange?.({ dirty: !!text.trim(), busy });
  }, [text, busy, onStateChange]);
  useEffect(() => {
    if (suspended) setMediaOpen(false);
  }, [suspended]);
  const speechText = useRef({ user: "", assistant: "" });
  const knownProposals = useRef<Proposal[]>([]);
  const activityReading = useRef(false);
  const loadActivity = useCallback(async () => {
    if (!owner.current || activityReading.current) return;
    const scope = taskId;
    activityReading.current = true;
    try {
      const activity = await request<{ jobs: ComputerJob[] }>(
        `/computer/jobs${scope ? `?task_id=${encodeURIComponent(scope)}` : ""}`,
      );
      if (alive.current && jobScope.current === scope) {
        const prior = seenJobs.current;
        const incoming = activity.jobs
          .filter(
            (job) =>
              !["succeeded", "failed", "cancelled", "expired"].includes(
                job.state,
              ) ||
              (prior && !prior.has(job.id)),
          )
          .map((job) => job.id);
        seenJobs.current = new Set(activity.jobs.map((job) => job.id));
        setAttentionJobs((old) =>
          [...new Set([...old, ...incoming])].slice(-20),
        );
        setJobs(activity.jobs);
        setJobsReadAt(Date.now());
        setJobsError(null);
      }
    } catch (reason) {
      if (alive.current && jobScope.current === scope) setJobsError(reason);
    } finally {
      activityReading.current = false;
    }
  }, [taskId]);
  useEffect(() => {
    setJobs([]);
    seenJobs.current = null;
    setAttentionJobs([]);
    setJobsReadAt(0);
    void loadActivity();
  }, [loadActivity]);
  useEffect(() => {
    window.addEventListener("desk:jobs", loadActivity);
    return () => window.removeEventListener("desk:jobs", loadActivity);
  }, [loadActivity]);
  async function actOnJob(job: ComputerJob, action: JobAction) {
    if (action === "cancel" ? jobCancelling : jobBusy) return;
    if (action === "cancel") setJobCancelling(job.id);
    else setJobBusy(job.id);
    setJobActionError(null);
    setJobActionNotice("");
    try {
      await requestJobAction(job, action);
      if (action === "verify" && isApplicationAction(job.action)) {
        setJobActionNotice(
          t(
            "The file was reopened and matches the verified operation.",
            "文件已重新打开核对，与已核验操作一致。",
          ),
        );
      }
      await loadActivity();
      void refresh();
    } catch (reason) {
      setJobActionError(reason);
      void loadActivity();
    } finally {
      if (action === "cancel") setJobCancelling(null);
      else setJobBusy(null);
    }
  }
  const turnText = (turn: { body: string; jobId?: string }) => {
    if (!immersive || expanded || !turn.jobId) return turn.body;
    const job = jobs.find((item) => item.id === turn.jobId);
    return job
      ? `${jobStateLabel(job.state, t)} · ${job.request.title}`
      : t(
          "Open the conversation for this action’s details.",
          "打开对话查看这项操作的详情。",
        );
  };
  const jobCard = (job: ComputerJob) => (
    <JobActionCard
      key={job.id}
      job={job}
      t={t}
      busy={!!jobBusy}
      cancelling={!!jobCancelling || offline}
      fresh={!jobsError && !offline && !stale && Date.now() - jobsReadAt < 6000}
      available={
        !!(isApplicationAction(job.action)
          ? data?.computer?.applications?.enabled &&
            data.computer.applications.configured
          : isDesktopAction(job.action)
            ? data?.computer?.desktop?.ready
            : isFolderAction(job.action)
              ? data?.computer?.folder?.configured
              : data?.computer?.enabled)
      }
      onAction={(action) => void actOnJob(job, action)}
    />
  );
  const language = t("en", "zh");
  const voiceActive = microphone;
  const omni =
    !!data?.voice.configured &&
    data.voice.provider === "qwen_omni" &&
    owner.current;
  const unavailable = !data || offline || stale;
  const openJobs = () => {
    setJobsOpened(true);
    setView("jobs");
    setMenu(false);
  };
  useEffect(() => {
    if (!followLatest.current) return;
    conversation.current?.scrollTo({
      top: conversation.current.scrollHeight,
      behavior: "instant",
    });
  }, [
    turns,
    proposals,
    transcript,
    liveMessage,
    notice,
    error,
    view,
    jobRevision,
  ]);
  function endVoice() {
    const engine = audio.current;
    audio.current = null;
    engine?.close();
    modeSwitching.current = false;
    setMicrophone(false);
    setBusy(false);
    setVoiceState("idle");
    setVoiceSlow(false);
    setSharing(false);
    setVisionBusy(false);
    setAttachments(false);
  }
  useEffect(() => {
    if (unavailable) endVoice();
  }, [unavailable]);
  useEffect(() => {
    const renewed = () => {
      conversationId.current = undefined;
      endVoice();
    };
    window.addEventListener("desk:session", renewed);
    return () => window.removeEventListener("desk:session", renewed);
  }, []);
  useEffect(() => {
    if (suspended && audio.current) endVoice();
  }, [suspended]);
  useEffect(() => {
    audio.current?.refreshContext();
  }, [data?.permissions?.version]);
  const previousTask = useRef(taskId);
  useEffect(() => {
    if (previousTask.current === taskId) return;
    previousTask.current = taskId;
    submissionGeneration.current += 1;
    if (pendingSubmission.current) setText(pendingSubmission.current);
    pendingSubmission.current = null;
    finishTranscript(true);
    endVoice();
    // Keep visible messages and unsent text, but never replay a different task's
    // model context. Reconnecting still requires the next explicit user input.
    conversationId.current = undefined;
    setNotice(
      t(
        "Discussion changed. Your next message starts a fresh context; earlier messages stay visible.",
        "讨论对象已切换。下一条消息会使用新的上下文，之前的消息仍可查看。",
      ),
    );
  }, [taskId]);
  useEffect(() => {
    if (immersive && (proposals.length > 0 || view !== "chat"))
      onExpandedChange?.(true);
  }, [immersive, proposals.length, view, onExpandedChange]);
  useEffect(() => {
    if (immersive && turns.at(-1)?.jobId) onExpandedChange?.(true);
  }, [turns, immersive, onExpandedChange]);
  useEffect(() => {
    if (immersive && !expanded) setView("chat");
  }, [immersive, expanded]);
  const ownerView = data?.principal.kind === "owner";
  const voiceWork = useVoiceWorkHandoff(t, taskId, suspended, endVoice);
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
        setReadError(null);
      }
    } catch (e) {
      if (alive.current) setReadError(e);
    }
    if (!ownerView) {
      if (alive.current) setCalls(null);
      return;
    }
    try {
      const audit = await request<{ calls: ToolCall[] }>(
        "/assistant/tool-calls",
      );
      if (alive.current) setCalls(audit.calls);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        if (alive.current) setCalls(null);
        return;
      }
      if (alive.current) setReadError(e);
    }
  }, [language, ownerView, loadActivity]);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      submissionGeneration.current += 1;
      const engine = audio.current;
      audio.current = null;
      engine?.close();
    };
  }, []);
  useEffect(() => {
    const tick = () => {
      if (!document.hidden && !suspended) void reload();
    };
    tick();
    const timer = setInterval(tick, 2000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [reload, suspended]);
  const showHttpReply = useCallback((submitted: string, result: Reply) => {
    setReply(result);
    conversationId.current = result.conversation_id;
    setLiveMessage("");
    setProgress([]);
    setError(
      result.permission_error ? new ApiError(result.permission_error) : null,
    );
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
          jobId: result.job?.id,
        },
      ].slice(-40),
    );
    setText((current) => (current === submitted ? "" : current));
    pendingHttp.current = null;
  }, []);
  useEffect(() => {
    const recovered = (event: Event) => {
      const { operation, result } = (
        event as CustomEvent<{
          operation: { path: string; body: object };
          result: Reply;
        }>
      ).detail;
      const pending = pendingHttp.current;
      if (
        !pending ||
        !alive.current ||
        pending.generation !== submissionGeneration.current ||
        operation.path !== "/assistant/messages/stream" ||
        JSON.stringify(operation.body) !== JSON.stringify(pending.body) ||
        typeof result?.message !== "string"
      )
        return;
      showHttpReply(pending.message, result);
      void reload();
    };
    window.addEventListener("desk:write-recovered", recovered);
    return () => window.removeEventListener("desk:write-recovered", recovered);
  }, [reload, showHttpReply]);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !text.trim() || unavailable || pendingJob) return;
    followLatest.current = true;
    const submitted = text;
    const previousHttp = pendingHttp.current;
    const generation = ++submissionGeneration.current;
    setBusy(true);
    setError(null);
    setNotice("");
    setReply(null);
    setLiveMessage("");
    setProgress([]);
    try {
      if (omni) {
        pendingSubmission.current = submitted;
        const engine = await connectConversation("text");
        if (!engine) throw new Error("VOICE_CONNECTION_FAILED");
        await engine.sendText(submitted);
        setText("");
        return;
      }
      const body = {
        message: submitted,
        language,
        task_id: taskId ?? null,
        conversation_id: conversationId.current ?? null,
      };
      pendingHttp.current = { body, generation, message: submitted };
      const result = (await writeStream(
        "/assistant/messages/stream",
        body,
        (state) => {
          if (alive.current && generation === submissionGeneration.current) {
            setLiveMessage(state.message);
            setProgress(state.tools);
          }
        },
      )) as Reply;
      if (!alive.current || generation !== submissionGeneration.current) return;
      showHttpReply(submitted, result);
      void reload();
      window.dispatchEvent(new Event("desk:jobs"));
    } catch (e) {
      if (!alive.current || generation !== submissionGeneration.current) return;
      if (e instanceof ApiError && e.code === "PENDING_WRITE") {
        pendingHttp.current = previousHttp;
        if (previousHttp) previousHttp.generation = generation;
      }
      if (!omni) setError(e);
      else {
        // No text was admitted yet. Keep the specific connection notice instead
        // of the generic HTTP-write "unknown result" warning.
        setError(null);
        if (audio.current)
          setNotice(
            t(
              "This message was not sent. Check the connection and try again.",
              "这条消息未发送，请检查连接后重试。",
            ),
          );
      }
      pendingSubmission.current = null;
      setBusy(false);
    } finally {
      if (!omni && generation === submissionGeneration.current) setBusy(false);
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
      if (omni) audio.current?.refreshContext();
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
  function finishTranscript(interrupted = false) {
    const speech = speechText.current;
    const id = Date.now();
    setTurns((old) =>
      [
        ...old,
        ...(speech.user
          ? [{ id, role: "user" as const, body: speech.user }]
          : []),
        ...(speech.assistant
          ? [
              {
                id: id + 1,
                role: "assistant" as const,
                body:
                  speech.assistant +
                  (interrupted ? t(" (interrupted)", "（已打断）") : ""),
              },
            ]
          : []),
      ].slice(-40),
    );
    speechText.current = { user: "", assistant: "" };
    setTranscript("");
  }
  async function switchToText() {
    if (!omni) {
      endVoice();
      return;
    }
    // Cancelling permission/connection setup must stop late capture immediately.
    if (voiceState === "connecting") {
      endVoice();
      return;
    }
    modeSwitching.current = true;
    setBusy(true);
    setMicrophone(false);
    setVoiceState("connecting");
    try {
      await audio.current?.setMode("text");
    } catch (e) {
      endVoice();
      setError(e);
    }
    queueMicrotask(() => composer.current?.focus());
  }
  async function newConversation() {
    submissionGeneration.current += 1;
    pendingHttp.current = null;
    const id = conversationId.current;
    endVoice();
    try {
      if (id)
        await request(`/voice/conversations/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
      conversationId.current = undefined;
      pendingSubmission.current = null;
      setTurns([]);
      speechText.current = { user: "", assistant: "" };
      setTranscript("");
      setNotice(
        t(
          "New conversation. Saved memories are kept.",
          "已开始新对话，已保存的记忆仍保留。",
        ),
      );
    } catch (e) {
      setError(e);
    }
    setMenu(false);
  }
  async function startVoice() {
    if (unavailable || busy) return;
    modeSwitching.current = true;
    setBusy(true);
    setMicrophone(true);
    setVoiceState("connecting");
    try {
      if (audio.current) await audio.current.setMode("voice");
      else await connectConversation("voice");
    } catch (e) {
      modeSwitching.current = false;
      setBusy(false);
      setMicrophone(false);
      setError(e);
    }
  }
  async function connectConversation(mode: "text" | "voice") {
    if (audio.current) return audio.current;
    if (unavailable || !data?.voice.configured) return null;
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
        voiceWork.observe(event);
        if (event.type === "ready") {
          if (modeSwitching.current) {
            modeSwitching.current = false;
            setBusy(false);
          }
          if (event.conversation_id)
            conversationId.current = event.conversation_id;
          setMicrophone((event.mode ?? mode) === "voice");
          setVoiceState("listening");
        }
        if (event.type === "turn_waiting" || event.type === "interrupted")
          setVoiceSlow(false);
        if (event.type === "turn_slow") setVoiceSlow(true);
        if (event.type === "turn_timing" && event.turn_id !== undefined) {
          setVoiceTimings((old) =>
            [
              ...old.filter((row) => row.turn_id !== event.turn_id),
              event as TurnMeasurement,
            ].slice(-20),
          );
          if (event.response_started) setVoiceSlow(false);
        }
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
        if (event.type === "turn_complete" || event.type === "interrupted") {
          finishTranscript(event.type === "interrupted");
          if (!modeSwitching.current) setBusy(false);
        }
        if (event.type === "transcript") {
          const role = event.role === "user" ? "user" : "assistant";
          if (role === "user" && event.text === pendingSubmission.current)
            pendingSubmission.current = null;
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
        if (event.type === "jobs_changed") {
          window.dispatchEvent(new Event("desk:jobs"));
          if (immersive) onExpandedChange?.(true);
        }
        if (event.type === "error") {
          modeSwitching.current = false;
          if (pendingSubmission.current) setText(pendingSubmission.current);
          pendingSubmission.current = null;
          audio.current = null;
          engine.close();
          setSharing(false);
          setVisionBusy(false);
          setNotice(
            event.code === "VOICE_TURN_TIMEOUT"
              ? t(
                  "This reply timed out. The microphone is off. Start again or type your request.",
                  "本轮回答等待超时，麦克风已关闭。可以重新开始交谈或改用文字输入。",
                )
              : event.code === "VOICE_UNGROUNDED_RESPONSE" ||
                  event.code === "ASSISTANT_TOOL_RETRY_LIMIT"
                ? t(
                    "I could not verify the latest result. This conversation has stopped; please try again.",
                    "暂时无法核实最新结果，本次连接已停止。请再试一次。",
                  )
                : event.code === "VOICE_MODEL_ACCESS_DENIED"
                  ? t(
                      "The provider denied access to this model. Check model access in the Qwen console. This connection has stopped.",
                      "千问拒绝访问这个模型。请在千问平台检查模型权限或开通状态，本次连接已停止。",
                    )
                  : event.code === "VOICE_CONNECT_TIMEOUT"
                    ? t(
                        "Voice connection timed out. The microphone is off; try again or type your request.",
                        "语音连接超时，麦克风已关闭。可以重试或改用文字输入。",
                      )
                    : t(
                        "Voice could not continue. The microphone is off. Check the connection or provider configuration.",
                        "语音未能继续，麦克风已关闭。请检查连接或服务配置。",
                      ),
          );
          setVoiceState("idle");
          setMicrophone(false);
          setBusy(false);
          if (
            [
              "TASK_NOT_FOUND",
              "PRIVATE_TASK_HIDDEN",
              "INVALID_TASK_CONTEXT",
              "TASK_CONTEXT_NOT_ALLOWED",
            ].includes(event.code ?? "")
          ) {
            setNotice(
              t(
                "This task is not available for this conversation. Review it in Tasks or end the task discussion.",
                "当前会话无法读取这件事务。请在事务中核对，或结束事务讨论。",
              ),
            );
          }
          if (event.code === "CONVERSATION_SCOPE_CHANGED") {
            conversationId.current = undefined;
            setNotice(
              t(
                "The discussion context changed. Send again to start with the selected task.",
                "讨论上下文已变化。再次发送会使用当前选中的事务开始新会话。",
              ),
            );
          }
          if (event.code === "CONVERSATION_NOT_FOUND") {
            conversationId.current = undefined;
            setNotice(
              t(
                "This conversation expired. Send again to start a new one with your saved memories.",
                "对话上下文已过期。再次发送将开始新对话，已保存记忆仍可使用。",
              ),
            );
          }
        }
        if (event.type === "rejected") {
          if (pendingSubmission.current) setText(pendingSubmission.current);
          pendingSubmission.current = null;
          setBusy(false);
          setNotice(
            t(
              "Wait for the current reply or stop it first.",
              "请等待当前回复，或先停止回复。",
            ),
          );
        }
        if (event.type === "closed" || event.type === "ended") {
          modeSwitching.current = false;
          if (pendingSubmission.current) setText(pendingSubmission.current);
          pendingSubmission.current = null;
          finishTranscript(true);
          audio.current = null;
          setVoiceState("idle");
          setSharing(false);
          setVisionBusy(false);
          setMicrophone(false);
          setBusy(false);
          if (event.reason === "memory_changed") {
            setNotice(
              t(
                "Saved memory changed. The next message will use the updated memory in a fresh context.",
                "记忆已更新。下一条消息会在新的对话上下文中使用最新记忆。",
              ),
            );
          }
        }
      });
      starting = engine;
      audio.current = engine;
      const url = new URL("/api/voice/ws", apiOrigin());
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      await engine.start(
        () =>
          handoverTicket(
            async () =>
              (
                await request<{ ticket: string }>("/voice/tickets", {
                  method: "POST",
                  body: "{}",
                })
              ).ticket,
            () => alive.current && audio.current === engine,
          ),
        language,
        url.href,
        {
          mode,
          conversationId: omni ? conversationId.current : undefined,
          taskId,
        },
      );
      return engine;
    } catch (e) {
      if (!alive.current || audio.current !== starting) return;
      endVoice();
      setError(e);
      setNotice(
        t(
          mode === "voice"
            ? "Check microphone permission and the connection."
            : "Check the configured Omni connection.",
          mode === "voice"
            ? "请检查麦克风权限和连接。"
            : "请检查已配置的 Omni 连接。",
        ),
      );
      return null;
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
      className={`workspace-panel assistant-panel ${immersive ? `phone-assistant ${expanded ? "expanded" : "compact"}` : ""}`}
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
      {voiceWork.panel}
      {mediaOpen && !suspended && (
        <MediaDevicePanel
          t={t}
          onClose={() => setMediaOpen(false)}
          voiceActive={voiceActive}
          canShare={
            voiceActive &&
            !!data?.voice.supports_images &&
            !unavailable &&
            voiceState !== "connecting"
          }
          provider={data?.voice.provider ?? ""}
          onShare={(video) => {
            if (!audio.current) throw new Error("VOICE_VISION_NOT_READY");
            audio.current.shareCameraFrame(video);
          }}
        />
      )}
      {taskTitle && (
        <p className="assistant-context-label">
          <span>
            {t("Discussing: ", "当前讨论：")}
            <strong>{taskTitle}</strong>
          </span>
          {onClearTask && (
            <button className="text-button" onClick={onClearTask}>
              {t("End task discussion", "结束事务讨论")}
            </button>
          )}
        </p>
      )}
      {immersive && !expanded && homeHint}
      <div className="assistant-toolbar">
        {workspace && view === "chat" && (
          <button
            className="text-button assistant-new-chat"
            disabled={busy}
            onClick={() => void newConversation()}
          >
            <SquarePen size={17} />
            {t("New chat", "新对话")}
          </button>
        )}

        {immersive && (
          <button
            className="text-button phone-conversation-toggle"
            onClick={() => onExpandedChange?.(!expanded)}
          >
            {expanded ? <ArrowLeft size={17} /> : <MoreHorizontal size={17} />}
            {expanded
              ? t("Back to Alice", "返回 Alice")
              : t("Conversation", "本次对话")}
          </button>
        )}
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
            {ownerView && (
              <button disabled={busy} onClick={() => void newConversation()}>
                {t("New conversation", "新对话")}
              </button>
            )}
            {audio.current && (
              <button onClick={endVoice}>{t("Disconnect", "断开连接")}</button>
            )}
            <button
              onClick={() => {
                setMenu(false);
                setMediaOpen(true);
              }}
            >
              <Camera size={18} />
              {t("Camera & microphone", "摄像头与麦克风")}
            </button>
            <button onClick={openJobs}>
              <FolderCheck size={18} />
              {t("File actions & activity", "文件操作与进度")}
            </button>
            {ownerView && (
              <button
                onClick={() => {
                  setView("activity");
                  setMenu(false);
                }}
              >
                {t("Tool activity", "工具记录")}
              </button>
            )}
            <a href="?surface=avatar" target="_blank" rel="noreferrer">
              <Box size={18} />
              {t("Character & appearance", "角色与外观")}
            </a>
            <button
              onClick={() => {
                setView("timing");
                setMenu(false);
              }}
            >
              {t("Response timing", "响应时间")}
            </button>
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
      {view === "activity" && <ToolActivity t={t} calls={calls} />}
      <section
        className="assistant-chat"
        hidden={view !== "chat"}
        aria-label={t("Conversation", "对话")}
      >
        <div
          className="assistant-conversation"
          ref={conversation}
          onScroll={(event) => {
            const node = event.currentTarget;
            if (node.clientHeight > 0)
              followLatest.current =
                node.scrollHeight - node.scrollTop - node.clientHeight < 80;
          }}
        >
          {!turns.length &&
            !transcript &&
            !proposals.length &&
            !voiceActive &&
            attentionJobs.length === 0 && (
              <div className="assistant-welcome">
                <h3>
                  {taskId
                    ? t("Let’s work through this task.", "一起看看这件事。")
                    : t("What can I help you with?", "今天想做些什么？")}
                </h3>
                <p>
                  {taskId
                    ? t(
                        "Share an update or discuss the next step.",
                        "说说当前进展，或讨论下一步。",
                      )
                    : t(
                        "Start with your calendar, or tell me what you want to work on.",
                        "可以先看看日历，或说说你想推进的事情。",
                      )}
                </p>
                {!taskId && (
                  <div className="assistant-starters">
                    {[
                      ["What is on today?", "今天的行程"],
                      ["What is on next week?", "下周的日程"],
                    ].map(([en, zh]) => (
                      <button
                        key={en}
                        type="button"
                        onClick={() => {
                          setText(t(en, zh));
                          composer.current?.focus();
                        }}
                      >
                        {t(en, zh)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          {(!immersive || expanded) &&
            jobs
              .filter(
                (job) =>
                  attentionJobs.includes(job.id) &&
                  !turns.some((turn) => turn.jobId === job.id),
              )
              .slice(0, 3)
              .map(jobCard)}
          {(immersive && !expanded
            ? turns.filter((turn) => turn.role === "assistant").slice(-1)
            : turns
          ).map((turn) => (
            <div className={`assistant-turn ${turn.role}`} key={turn.id}>
              <p>{turnText(turn)}</p>
              {turn.jobId &&
                (!immersive || expanded) &&
                jobs.filter((job) => job.id === turn.jobId).map(jobCard)}
            </div>
          ))}
          {liveMessage && (
            <p className="assistant-turn assistant" aria-live="polite">
              {liveMessage}
            </p>
          )}
          {busy && progress.length > 0 && (
            <ol className="tool-progress" aria-live="polite">
              {progress.map((item, index) => (
                <li key={`${index}-${item.tool}`}>
                  <span>{item.tool}</span>
                  <span>{progressLabel(item.phase, language)}</span>
                </li>
              ))}
            </ol>
          )}
          {transcript && (
            <p className="assistant-turn voice-transcript" aria-live="polite">
              {transcript}
            </p>
          )}
          {pendingJob && (
            <button
              className="secondary"
              disabled={!!jobBusy}
              onClick={async () => {
                setJobBusy("recovery");
                try {
                  await retryPending();
                  setJobActionError(null);
                  await loadActivity();
                  void refresh();
                } catch (reason) {
                  setJobActionError(reason);
                } finally {
                  setJobBusy(null);
                }
              }}
            >
              {t("Recover previous action", "核对上一项操作")}
            </button>
          )}
          {!!jobActionNotice && <p role="status">{jobActionNotice}</p>}
          {!!jobActionError && (
            <p className="error-message" role="alert">
              {errorText(jobActionError, t)}
            </p>
          )}
          {jobs.length > 0 &&
            (turns.length > 0 || attentionJobs.length > 0) &&
            (!immersive || expanded) && (
              <button className="text-button" onClick={openJobs}>
                {t("See all file activity", "查看全部文件活动")}
              </button>
            )}
          {!!jobsError && (
            <p className="error-message" role="alert">
              {t(
                "Unable to refresh file actions. Existing actions remain on your desk.",
                "暂时无法刷新文件操作，已有操作仍保留在桌面服务中。",
              )}
            </p>
          )}
          {immersive && !expanded && jobAttention > 0 && (
            <button
              className="assistant-attention"
              onClick={() => onExpandedChange?.(true)}
            >
              <FolderCheck size={16} />
              {t(
                `${jobAttention} action(s) need your attention`,
                `${jobAttention} 项操作需要你处理`,
              )}
            </button>
          )}
          {busy && (
            <p className="assistant-pending" role="status">
              {t("Thinking…", "处理中…")}
            </p>
          )}
          {proposals.map((proposal) => (
            <ProposalActionCard
              key={proposal.id}
              proposal={proposal}
              t={t}
              busy={busy || unavailable}
              onDecision={(action) => void decide(proposal.id, action)}
            />
          ))}

          {notice && (
            <p className="assistant-notice" role="status">
              {notice}
            </p>
          )}
          {!!readError && (
            <p className="assistant-notice" role="status">
              {t(
                "Unable to refresh current actions. I will retry when the connection returns.",
                "暂时无法刷新当前操作，连接恢复后会重试。",
              )}
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
        <div
          className="assistant-input-area"
          id={workspace ? "desktop-chat-composer" : undefined}
        >
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
              {voiceSlow && (
                <p role="status">
                  {t(
                    "Still waiting for a reply. You can also use text.",
                    "回答仍在准备中，也可以改用文字输入。",
                  )}
                </p>
              )}
              <div className="assistant-call-actions">
                <button
                  className="icon-button"
                  aria-label={t("Camera & microphone", "摄像头与麦克风")}
                  onClick={() => setMediaOpen(true)}
                >
                  <Camera size={20} />
                </button>
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
                  aria-label={
                    omni
                      ? t("Switch to text", "改为文字")
                      : t("End conversation", "结束交谈")
                  }
                  onClick={() => void switchToText()}
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
                rows={1}
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
                <button
                  type="button"
                  className="icon-button assistant-camera"
                  aria-label={t("Camera & microphone", "摄像头与麦克风")}
                  onClick={() => setMediaOpen(true)}
                >
                  <Camera size={20} />
                </button>
                {busy && omni ? (
                  <button
                    type="button"
                    className="assistant-mic"
                    aria-label={t("Stop reply", "停止回复")}
                    onClick={() => audio.current?.interrupt()}
                  >
                    <Square size={17} />
                  </button>
                ) : text.trim() ? (
                  <button
                    className="assistant-mic"
                    disabled={busy || unavailable || !!pendingJob}
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
                      "Only images you choose are shared in this conversation.",
                      "仅分享你选定的画面。",
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
          <PermissionControl t={t} />
          <p className="assistant-caption">
            {voiceActive
              ? voiceState === "connecting"
                ? t("Preparing voice…", "正在准备语音…")
                : t(
                    "Speak naturally. Your mic is on.",
                    "直接交谈，麦克风已开启。",
                  )
              : omni
                ? t("Qwen Omni · microphone off", "Qwen Omni · 麦克风已关闭")
                : data?.text_ai?.configured
                  ? data?.permissions?.mode === "full"
                    ? t(
                        "Actions follow your permission setting.",
                        "操作遵循你的权限设置。",
                      )
                    : t("Review changes before saving.", "修改会先交给你确认。")
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
      <section
        hidden={view !== "timing"}
        className="assistant-secondary assistant-help"
      >
        <h3>{t("Response timing", "响应时间")}</h3>
        <p>
          {t(
            "Time from detected speech end to speaker output. First sound can include filler; post-tool audio is not a correctness score.",
            "从检测到说话结束到扬声器输出。首音可能包含铺垫，工具后播音也不代表答案正确性已验证。",
          )}
        </p>
        {!voiceTimings.length && (
          <p>
            {t(
              "Timing appears here after a voice reply starts playing.",
              "语音回复开始播放后，这里会显示计时。",
            )}
          </p>
        )}
        {voiceTimings.map((row) => (
          <article key={row.turn_id}>
            <strong>
              {t("Turn ", "第 ")}
              {row.turn_id}
              {t("", " 轮")}
            </strong>
            <p>
              {row.first_text_ms != null && (
                <>
                  {t("Text received by server: ", "服务器收到文字：")}
                  {(row.first_text_ms / 1000).toFixed(2)} s ·{" "}
                </>
              )}
              {t("First sound: ", "首音：")}
              {row.first_played_ms == null
                ? "—"
                : (row.first_played_ms / 1000).toFixed(2) + " s"}
              {" · "}
              {t("After tool: ", "工具后播音：")}
              {row.post_tool_played_ms == null
                ? "—"
                : (row.post_tool_played_ms / 1000).toFixed(2) + " s"}
            </p>
            <small>
              {row.timing_source === "output_timestamp"
                ? t("Browser output clock", "浏览器输出时钟")
                : t("Estimated output time", "输出时间估计")}
            </small>
          </article>
        ))}
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
            "Ask about today or next week, keep track of a task, or prepare a note. Changes wait for your review.",
            "可以查询今天或下周的日程、跟进一件事务，或准备一份笔记。修改会先交给你核对。",
          )}
        </p>
        <ul>
          <li>{t("What is on today?", "今天的行程")}</li>
          <li>{t("What is on next week?", "下周有什么日程？")}</li>
          <li>{t("Track: finish the project report", "跟进：完成项目报告")}</li>
          <li>
            {t("Remember: I prefer morning meetings", "记住：我喜欢上午开会")}
          </li>
          <li>{t("Save note: project ideas", "保存笔记：项目想法")}</li>
        </ul>
        <p>
          {t(
            "When Omni is configured, text and voice share the same model and conversation. Typing does not open the microphone. Short-term context expires after 30 minutes without use or a server restart; saved memories remain. New conversation clears short-term context.",
            "配置 Omni 后，文字和语音共用同一模型与对话，打字不会开启麦克风。短期上下文在闲置30分钟或服务重启后失效；已保存的记忆仍保留。新对话会清除短期上下文。",
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
