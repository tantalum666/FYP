import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Send, Sparkles } from "lucide-react";
import { ApiError, errorText, request } from "../api";
import type { EventInput, Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { VoiceAudio } from "./audio";
import { VoiceWorkPanel } from "./voiceWork/VoiceWorkPanel";
import { emptyVoiceInputs, reduceVoiceInputs } from "./voiceWork/types";
import type { WorkGoalRequest } from "./agent/types";
import { useDraftGuard } from "../components/DraftGuard";
import type { Task, TaskInput } from "./taskTypes";
import { apiOrigin } from "../native";
import { DateTime } from "luxon";
import { ComputerJobsPanel } from "./ComputerJobsPanel";
import { RoutinesPanel } from "./RoutinesPanel";
import { ResponsibilitiesPanel } from "./responsibilities/ResponsibilitiesPanel";
import { RunPanel } from "./agent/RunPanel";
import { BrowserWorkflowPanel } from "./browser/BrowserWorkflowPanel";
import { ConnectorReviewPanel } from "./connectors/ConnectorReviewPanel";
import { Modal } from "../components/Dialogs";
import { ResponseFence } from "./personal/responseFence";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { usePersonalContext } from "./personal/usePersonalContext";
import {
  personalContextVisible,
  canSendText,
  conversationSwitch,
} from "./personal/types";
import type { MemoryCategory } from "./personal/types";
import {
  PersonalContextPanel,
  ModeLabel,
} from "./personal/PersonalContextPanel";
import { MutationFeedback } from "./personal/MutationFeedback";
import { memoryCategory } from "./personal/MemoryPanel";

interface Proposal {
  id: string;
  kind:
    | "create"
    | "change"
    | "output"
    | "task_create"
    | "task_change"
    | "memory_create"
    | "memory_update"
    | "memory_forget";
  expires_at: string;
  data: {
    content?: string;
    category?: MemoryCategory;
    memory_id?: string;
    expected_version?: number;
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
  conversation_id?: string | null;
  history_saved?: boolean;
}

export function AssistantPanel({
  t,
  taskId,
  displayMode = false,
}: {
  t: Translate;
  taskId?: string;
  displayMode?: boolean;
}) {
  const { data, refresh, offline, stale } = useWorkspace();
  const [text, setText] = useState(""),
    [error, setError] = useState<unknown>(null);
  const mutation = usePrivateMutation();
  const busy = mutation.busy;
  const locked = busy || mutation.pending;
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [switchTo, setSwitchTo] = useState<{ id: string | null } | null>(null);
  const posture = data?.posture;
  const displayConcealed =
    displayMode &&
    (!posture ||
      (posture.preferences.enabled &&
        posture.preferences.privacy_when_away &&
        (!posture.connected ||
          ["absent", "unknown", "paused"].includes(posture.status))));
  const contextVisible = personalContextVisible(
    data?.principal.kind === "owner",
    data?.personal_context_visible,
    offline || displayConcealed,
    stale,
  );
  const personal = usePersonalContext(contextVisible, conversationId);
  const contentVisible =
    !!data &&
    !offline &&
    !stale &&
    !displayConcealed &&
    (data.principal.kind !== "owner" || contextVisible);
  const contentVisibleNow = useRef(contentVisible);
  contentVisibleNow.current = contentVisible;
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const [contextEpoch, setContextEpoch] = useState(0);
  const identity = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${sessionEpoch}`;
  const fence = useRef(new ResponseFence());
  fence.current.update(
    `${identity}:${contextEpoch}:${apiOrigin()}:${data?.voice.config_revision ?? ""}`,
    contentVisible,
  );
  const privacyEpoch = fence.current.version;
  const previousIdentity = useRef(identity);
  const currentIdentity = useRef(identity);
  currentIdentity.current = identity;
  const currentText = useRef(text);
  currentText.current = text;
  const transcriptEpoch = useRef(-1),
    proposalEpoch = useRef(-1);
  useEffect(() => {
    const changed = () => {
      fence.current.update(`invalidated:${crypto.randomUUID()}`, false);
      voiceGeneration.current += 1;
      audio.current?.close();
      setSessionEpoch((x) => x + 1);
    };
    const contextChanged = () => {
      fence.current.update(`invalidated:${crypto.randomUUID()}`, false);
      voiceGeneration.current += 1;
      audio.current?.close();
      setContextEpoch((x) => x + 1);
    };
    window.addEventListener("desk:session", changed);
    window.addEventListener("desk:personal-context", contextChanged);
    return () => {
      window.removeEventListener("desk:session", changed);
      window.removeEventListener("desk:personal-context", contextChanged);
    };
  }, []);
  const [reply, setReply] = useState<(Reply & { viewEpoch: number }) | null>(
      null,
    ),
    [proposals, setProposals] = useState<Proposal[]>([]),
    [notice, setNotice] = useState("");
  const [voiceState, setVoiceState] = useState("idle"),
    [transcript, setTranscript] = useState({ user: "", assistant: "" });
  const [voiceInputs, setVoiceInputs] = useState(emptyVoiceInputs);
  const [voiceView, setVoiceView] = useState(0);
  const [speechMuted, setSpeechMuted] = useState(false);
  const voiceGeneration = useRef(0);
  const voiceActive = useRef(false);
  const audio = useRef<VoiceAudio | null>(null),
    alive = useRef(true);
  const speechText = useRef({ user: "", assistant: "" });
  const knownProposals = useRef<Proposal[]>([]);
  const proposalRequest = useRef(0);
  const [reviewProposal, setReviewProposal] = useState<string | null>(null);
  const [reviewBrowserJob, setReviewBrowserJob] = useState<{
    id: string;
    viewEpoch: number;
  } | null>(null);
  const [reviewConnectorIntent, setReviewConnectorIntent] = useState<{
    id: string;
    viewEpoch: number;
  } | null>(null);
  const [workGoal, setWorkGoal] = useState<
    (WorkGoalRequest & { viewEpoch: number }) | null
  >(null);
  const proposalNodes = useRef(new Map<string, HTMLElement>());
  const language = t("en", "zh");
  useDraftGuard(!!text.trim() || mutation.pending, busy);
  function selectConversation(id: string | null) {
    setVoiceInputs(emptyVoiceInputs());
    setVoiceView((x) => x + 1);
    setConversationId(id);
    setReply(null);
    setText("");
    setSwitchTo(null);
  }
  function requestConversation(id: string | null, mutationComplete = false) {
    const decision = conversationSwitch(
      conversationId,
      id,
      !!text.trim(),
      locked && !mutationComplete,
      voiceState !== "idle",
    );
    if (decision === "confirm") setSwitchTo({ id });
    else if (decision === "switch") selectConversation(id);
  }
  const reload = useCallback(async () => {
    if (!contentVisibleNow.current) return;
    const requestId = ++proposalRequest.current;
    const epoch = fence.current.capture();
    try {
      const next = await request<{ proposals: Proposal[] }>(
        "/assistant/proposals",
      );
      if (
        alive.current &&
        fence.current.accepts(epoch) &&
        proposalRequest.current === requestId
      ) {
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
        proposalEpoch.current = epoch;
        knownProposals.current = next.proposals;
        setProposals(next.proposals);
        return next.proposals;
      }
    } catch (e) {
      if (alive.current && proposalRequest.current === requestId) setError(e);
    }
  }, [language, privacyEpoch]);
  useEffect(() => {
    if (!reviewProposal || !contentVisible) return;
    const node = proposalNodes.current.get(reviewProposal);
    if (!node) return;
    const frame = requestAnimationFrame(() => {
      node.scrollIntoView({ block: "center" });
      node.focus({ preventScroll: true });
      setReviewProposal(null);
    });
    return () => cancelAnimationFrame(frame);
  }, [reviewProposal, proposals, contentVisible]);
  useEffect(() => {
    alive.current = true;
    void reload();
    const timer = setInterval(() => void reload(), 2000);
    return () => {
      alive.current = false;
      proposalRequest.current += 1;
      clearInterval(timer);
      audio.current?.close();
      voiceActive.current = false;
    };
  }, [reload]);
  useEffect(() => {
    if (previousIdentity.current !== identity) {
      previousIdentity.current = identity;
      setText("");
      mutation.clear();
      setConversationId(null);
      setSwitchTo(null);
    }
    setReply(null);
    setReviewProposal(null);
    setReviewBrowserJob(null);
    setReviewConnectorIntent(null);
    setWorkGoal(null);
    setTranscript({ user: "", assistant: "" });
    setVoiceInputs(emptyVoiceInputs());
    setVoiceView((x) => x + 1);
    setSpeechMuted(false);
    voiceGeneration.current += 1;
    setProposals([]);
    knownProposals.current = [];
    speechText.current = { user: "", assistant: "" };
    audio.current?.close();
    voiceActive.current = false;
    setVoiceState("idle");
  }, [privacyEpoch]);
  useEffect(() => {
    if (voiceState !== "idle") return;
    const timer = setTimeout(
      () => {
        setVoiceInputs(emptyVoiceInputs());
        setTranscript({ user: "", assistant: "" });
        speechText.current = { user: "", assistant: "" };
        setVoiceView((x) => x + 1);
      },
      5 * 60 * 1000,
    );
    return () => clearTimeout(timer);
  }, [voiceState, voiceView]);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!contentVisibleNow.current) return;
    if (
      !canSendText(
        text,
        locked,
        conversationId,
        personal.settings,
        contextVisible,
      )
    )
      return;
    setError(null);
    setNotice("");
    const epoch = fence.current.capture(),
      senderIdentity = identity,
      sentText = text;
    await mutation.run<Reply>(
      "/assistant/messages",
      {
        message: text,
        language,
        task_id: taskId ?? null,
        conversation_id: conversationId,
      },
      async (result) => {
        if (!alive.current) return;
        if (
          currentIdentity.current === senderIdentity &&
          currentText.current === sentText
        )
          setText("");
        if (!fence.current.accepts(epoch)) return;
        setReply({ ...result, viewEpoch: epoch });
        if (conversationId && result.history_saved === false)
          setNotice(
            t(
              "This reply was not saved to conversation history.",
              "此回复未保存到会话历史。",
            ),
          );
        await reload();
        await personal.reload(true);
        window.dispatchEvent(new Event("desk:jobs"));
      },
    );
  }
  async function decide(id: string, action: "confirm" | "cancel") {
    if (locked || offline || stale) return;
    setError(null);
    const kind = proposals.find((p) => p.id === id)?.kind;
    await mutation.run<{ queued?: boolean; kind?: string }>(
      `/assistant/proposals/${id}/decisions`,
      { action },
      async (result) => {
        setNotice(
          result.queued
            ? t(
                "Action queued. Check the device receipt for its result.",
                "动作已排队，请在设备回执中查看结果。",
              )
            : action === "cancel"
              ? t("Draft cancelled.", "草稿已取消。")
              : (result.kind ?? kind)?.startsWith("memory_")
                ? t(
                    "Memory decision recorded. Review Personal memories for the current result.",
                    "记忆决定已记录，请在个人记忆中核对当前结果。",
                  )
                : (result.kind ?? kind)?.startsWith("task_")
                  ? t(
                      "Task saved. Its progress is kept between conversations.",
                      "事务已保存，进展会在交谈之间保留。",
                    )
                  : t("Saved to your calendar.", "已保存到日历。"),
        );
        await reload();
        await refresh();
        await personal.reload(true);
        window.dispatchEvent(new Event("desk:calendar"));
        window.dispatchEvent(new Event("desk:tasks"));
      },
    );
  }
  function clearVoiceDisplay() {
    setVoiceInputs(emptyVoiceInputs());
    setTranscript({ user: "", assistant: "" });
    speechText.current = { user: "", assistant: "" };
  }
  async function startVoice() {
    if (
      !contentVisibleNow.current ||
      voiceActive.current ||
      !fence.current.accepts(privacyEpoch)
    )
      return;
    const epoch = privacyEpoch;
    setError(null);
    voiceActive.current = true;
    setVoiceState("connecting");
    setTranscript({ user: "", assistant: "" });
    setVoiceInputs(emptyVoiceInputs());
    setVoiceView((x) => x + 1);
    setSpeechMuted(false);
    voiceGeneration.current += 1;
    speechText.current = { user: "", assistant: "" };
    const generation = voiceGeneration.current;
    try {
      const engine = new VoiceAudio(
        (event) => {
          if (
            !alive.current ||
            !fence.current.accepts(epoch) ||
            generation !== voiceGeneration.current
          )
            return;
          if (event.type === "ready") setVoiceState("listening");
          if (event.type === "state" && event.state) setVoiceState(event.state);
          if (event.type === "audio" && !event.suppressed)
            setVoiceState("speaking");
          if (event.type === "speech_muted") {
            setSpeechMuted(true);
            setVoiceState("listening");
          }
          if (event.type === "speech_resumed") setSpeechMuted(false);
          if (event.type === "voice_input") {
            transcriptEpoch.current = epoch;
            setVoiceInputs((state) => reduceVoiceInputs(state, event));
          }
          if (event.type === "turn_complete" || event.type === "interrupted")
            setVoiceState("listening");
          if (
            event.type === "transcript" &&
            ["user", "assistant"].includes(event.role ?? "")
          ) {
            transcriptEpoch.current = epoch;
            // Legacy user display is never parsed or offered as a Work candidate.
            const role = event.role as "user" | "assistant";
            speechText.current[role] = (
              event.final
                ? (event.text ?? "")
                : speechText.current[role] + (event.text ?? "")
            ).slice(-3000);
            setTranscript({ ...speechText.current });
          }
          if (event.type === "proposal" || event.type === "proposals_changed")
            void reload();
          if (event.type === "jobs_changed")
            window.dispatchEvent(new Event("desk:jobs"));
          if (event.type === "error") {
            if (event.code === "VOICE_CONTEXT_CHANGED") {
              setError(new ApiError(event.code));
              setTranscript({ user: "", assistant: "" });
              setVoiceInputs(emptyVoiceInputs());
              setVoiceView((x) => x + 1);
              setSpeechMuted(false);
              voiceGeneration.current += 1;
              speechText.current = { user: "", assistant: "" };
              voiceActive.current = false;
              setVoiceState("idle");
              return;
            }
            clearVoiceDisplay();
            setNotice(
              t(
                "Voice could not continue. Check the connection or provider configuration.",
                "语音未能继续，请检查连接或服务配置。",
              ),
            );
            voiceActive.current = false;
            setVoiceState("idle");
          }
          if (event.type === "closed" || event.type === "ended") {
            clearVoiceDisplay();
            voiceActive.current = false;
            setVoiceState("idle");
          }
        },
        () =>
          alive.current &&
          fence.current.accepts(epoch) &&
          generation === voiceGeneration.current,
      );
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
      if (
        !alive.current ||
        !fence.current.accepts(epoch) ||
        generation !== voiceGeneration.current
      )
        return;
      voiceActive.current = false;
      setVoiceState("idle");
      setError(e);
      setNotice(
        t(
          "Microphone permission and a configured voice service are required.",
          "需要麦克风权限以及已配置的语音服务。",
        ),
      );
    }
  }
  return (
    <div className="workspace-panel assistant-panel">
      <div className="workspace-state">
        <Sparkles />
        <div>
          <h3>{t("A little help with your day", "帮你安排一天")}</h3>
          <p>
            {t(
              "Check your calendar, track a task or update its progress.",
              "查询日历、跟进事务，或补充进展后检查保存。",
            )}
          </p>
        </div>
      </div>
      <div className="assistant-voice-row">
        <div>
          <strong>
            {voiceState === "idle"
              ? data?.voice.configured
                ? t("Voice ready to connect", "语音可连接")
                : t("Voice service not configured", "语音服务未配置")
              : t("Conversation active", "正在交谈")}
          </strong>
          <small>
            {data?.voice.configured
              ? `${data.voice.provider} · ${data.voice.model}`
              : t(
                  "Local calendar and task tools are available below.",
                  "下方本地日历和事务工具可以使用。",
                )}
          </small>
        </div>
        {voiceState === "idle" ? (
          <button
            className="secondary"
            disabled={!data?.voice.configured || locked || !contentVisible}
            onClick={() => void startVoice()}
          >
            <Mic size={18} />
            {t("Start conversation", "开始交谈")}
          </button>
        ) : (
          <button
            className="secondary"
            onClick={() => {
              voiceGeneration.current += 1;
              audio.current?.close();
              clearVoiceDisplay();
              voiceActive.current = false;
              setVoiceState("idle");
            }}
          >
            <MicOff size={18} />
            {t("End conversation", "结束交谈")}
          </button>
        )}
      </div>
      <p className="workspace-hint">
        <a href="?surface=avatar" target="_blank" rel="noopener">
          {t("Open 3D companion", "打开3D虚拟伙伴")}
        </a>
        {" · "}
        {t(
          "Full-body character, expressions and voice motion",
          "全身角色、表情与语音口型",
        )}
      </p>
      {voiceState !== "idle" && (
        <>
          <p role="status">
            {t(
              "Speak naturally. You can interrupt; no need to hold a button.",
              "直接交谈，可以插话，不需要按住按钮。",
            )}
          </p>
          <button
            className="text-button"
            onClick={() => audio.current?.interrupt()}
          >
            {t("Stop speaking", "停止播报")}
          </button>
          {speechMuted && (
            <>
              <p role="status">
                {t(
                  "Speech playback is muted. Existing work and physical-output controls are unchanged.",
                  "语音播放已静音，已有工作及实体输出控制不变。",
                )}
              </p>
              <button
                className="secondary"
                onClick={() => audio.current?.hearAgain()}
              >
                {t("Hear speech again", "重新播放语音")}
              </button>
            </>
          )}
        </>
      )}
      <p className="workspace-hint">
        {t(
          "Voice transcripts are temporary and are not added to saved conversations or memories automatically.",
          "语音转写仅临时显示，不会自动加入已保存会话或记忆。",
        )}
      </p>
      {fence.current.accepts(transcriptEpoch.current) && (
        <>
          {!voiceInputs.inputs.length && transcript.user && (
            <p className="assistant-reply">
              {t("Voice input: ", "语音输入：")}
              {transcript.user}
            </p>
          )}
          {transcript.assistant && (
            <p className="assistant-reply" aria-live="polite">
              {t("Desk Companion: ", "Desk Companion：")}
              {transcript.assistant}
            </p>
          )}
          <VoiceWorkPanel
            key={`${privacyEpoch}:${voiceView}`}
            state={voiceInputs}
            t={t}
            fence={fence.current}
            owner={contextVisible}
            onInvalidated={() => {
              fence.current.update(
                `voice-invalidated:${crypto.randomUUID()}`,
                false,
              );
              voiceGeneration.current += 1;
              audio.current?.close();
              setContextEpoch((x) => x + 1);
            }}
            onHandoff={(goal) => {
              if (
                !contextVisible ||
                !fence.current.accepts(transcriptEpoch.current)
              )
                return;
              voiceGeneration.current += 1;
              audio.current?.close();
              clearVoiceDisplay();
              voiceActive.current = false;
              setVoiceState("idle");
              setWorkGoal({ ...goal, viewEpoch: fence.current.capture() });
              setVoiceInputs(emptyVoiceInputs());
              setTranscript({ user: "", assistant: "" });
              speechText.current = { user: "", assistant: "" };
            }}
          />
        </>
      )}
      {contextVisible ? (
        <PersonalContextPanel
          context={personal}
          selected={conversationId}
          onSelect={requestConversation}
          mutation={mutation}
          draftDirty={!!text.trim()}
          voiceActive={voiceState !== "idle"}
          t={t}
        />
      ) : (
        <p className="workspace-hint personal-private-notice">
          {t(
            "Saved conversations and personal memories require a current owner connection with private details visible.",
            "查看已保存会话与个人记忆需要拥有者连接正常，并允许显示私人详情。",
          )}
        </p>
      )}
      {conversationId && !contextVisible && (
        <p role="status">
          {t(
            "Private conversation hidden. Reconnect before continuing.",
            "私人会话已隐藏，恢复连接后才能继续。",
          )}
        </p>
      )}
      <form onSubmit={send} hidden={!contentVisible}>
        <label className="field">
          {t("Your request", "你的要求")}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={locked}
            required
            maxLength={3000}
            rows={3}
            placeholder={
              taskId
                ? t(
                    "What changed since your last update?",
                    "上次记录后，有什么新进展？",
                  )
                : t("Track: finish the project report", "跟进：完成项目报告")
            }
          />
        </label>
        <div className="workspace-inline-actions">
          <button
            className="primary"
            disabled={
              !canSendText(
                text,
                locked,
                conversationId,
                personal.settings,
                contextVisible,
              )
            }
          >
            <Send size={16} />
            {busy ? t("Preparing…", "处理中…") : t("Send", "发送")}
          </button>
          {data?.principal.kind === "owner" && (
            <button
              type="button"
              className="secondary"
              disabled={
                !contextVisible ||
                locked ||
                voiceState !== "idle" ||
                !text.trim()
              }
              onClick={() => {
                if (!contentVisibleNow.current || locked || !text.trim())
                  return;
                setWorkGoal({
                  id: crypto.randomUUID(),
                  text: text.trim(),
                  viewEpoch: fence.current.capture(),
                });
              }}
            >
              {t("Work on this…", "作为工作目标…")}
            </button>
          )}
          {!taskId && (
            <button
              type="button"
              className="text-button"
              disabled={locked}
              onClick={() => setText(t("What is on today?", "今天的行程"))}
            >
              {t("Today’s briefing", "今日简报")}
            </button>
          )}
        </div>
      </form>
      <p className="workspace-hint">
        {data?.text_ai?.configured
          ? t(
              "AI text is connected to your configured provider. Confirm drafts before they change anything.",
              "文字AI使用已配置的服务；草稿需确认后才会修改记录。",
            )
          : t(
              "Local rules: use Track: report to create a task, or discuss a saved task to record progress. AI voice is a separate connection.",
              "本地规则：用“跟进：报告”创建事务，或在事务内记录进展。AI语音单独连接。",
            )}
      </p>
      {reply && fence.current.accepts(reply.viewEpoch) && (
        <div className="assistant-reply" role="status">
          <ModeLabel mode={reply.mode} t={t} />
          <p>{reply.message}</p>
          {reply.proposal && (
            <small>
              {t(
                "A proposal is not a completed action. Review the current draft below.",
                "提案不是已完成动作，请检查下方当前草稿。",
              )}
            </small>
          )}
        </div>
      )}
      {proposals
        .filter(
          (p) =>
            fence.current.accepts(proposalEpoch.current) &&
            (!p.kind.startsWith("memory_") || contextVisible),
        )
        .map((p) => {
          const memoryProposal = p.kind.startsWith("memory_");
          const originalMemory = personal.memories.find(
            (m) => m.id === p.data.memory_id,
          );
          const memoryReady =
            !memoryProposal ||
            (p.kind === "memory_create"
              ? !!p.data.content
              : !!originalMemory &&
                originalMemory.version === p.data.expected_version);
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
          return (
            <article
              className="assistant-proposal"
              key={p.id}
              tabIndex={-1}
              ref={(node) => {
                if (node) proposalNodes.current.set(p.id, node);
                else proposalNodes.current.delete(p.id);
              }}
            >
              <span className="workspace-eyebrow">
                {t("Review before saving", "保存前检查")}
              </span>
              <h3>
                {memoryProposal
                  ? p.kind === "memory_create"
                    ? t("Remember this", "记住此内容")
                    : p.kind === "memory_update"
                      ? t("Correct a memory", "更正记忆")
                      : t("Forget a memory", "忘记记忆")
                  : (task?.title ??
                    event?.title ??
                    (p.kind === "output"
                      ? t("Device feedback", "设备反馈")
                      : t("Change calendar event", "修改日历事项")))}
              </h3>
              {memoryProposal ? (
                <>
                  {originalMemory && (
                    <p className="personal-text">
                      {t("Current: ", "当前：")}
                      {originalMemory.content}
                    </p>
                  )}
                  {p.data.content && (
                    <p className="personal-text">{p.data.content}</p>
                  )}
                  {p.data.category && (
                    <p>{memoryCategory(p.data.category, t)}</p>
                  )}
                  {!memoryReady && (
                    <p role="alert">
                      {t(
                        "The target memory is missing or changed. Refresh and prepare a new draft.",
                        "目标记忆不存在或已变化，请刷新并重新准备草稿。",
                      )}
                    </p>
                  )}
                  <p>
                    {p.kind === "memory_forget"
                      ? t(
                          "Removes this active memory from future context. Separate saved conversations and data already sent to providers are not erased.",
                          "后续上下文不再使用此有效记忆，独立保存的会话及已发送提供商的数据不会因此删除。",
                        )
                      : t(
                          "Saved only if you approve. This does not grant the assistant permission to act.",
                          "仅在你批准后保存，不会授予助理执行动作的权限。",
                        )}
                  </p>
                </>
              ) : task ? (
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
                  disabled={
                    locked ||
                    offline ||
                    stale ||
                    !memoryReady ||
                    Date.parse(p.expires_at) <= Date.now()
                  }
                  onClick={() => void decide(p.id, "confirm")}
                >
                  {t("Confirm & save", "确认并保存")}
                </button>
                <button
                  className="secondary"
                  disabled={locked || offline || stale}
                  onClick={() => void decide(p.id, "cancel")}
                >
                  {t("Cancel draft", "取消草稿")}
                </button>
              </div>
            </article>
          );
        })}
      <MutationFeedback mutation={mutation} t={t} />
      {switchTo && (
        <Modal
          title={t("Leave this unsent message?", "离开未发送的消息？")}
          closeLabel={t("Keep editing", "继续编辑")}
          onClose={() => setSwitchTo(null)}
        >
          <p>
            {t(
              "Changing conversations discards the text still in the request box. It has not been sent or saved.",
              "切换会话会放弃输入框中未发送的文字，这些文字尚未发送或保存。",
            )}
          </p>
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="primary"
              onClick={() => setSwitchTo(null)}
            >
              {t("Keep editing", "继续编辑")}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => selectConversation(switchTo.id)}
            >
              {t("Discard draft and switch", "放弃草稿并切换")}
            </button>
          </div>
        </Modal>
      )}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      <RunPanel
        t={t}
        visibleOverride={!displayConcealed}
        initialGoal={
          contextVisible &&
          workGoal &&
          fence.current.accepts(workGoal.viewEpoch)
            ? workGoal
            : undefined
        }
        onGoalHandled={() => setWorkGoal(null)}
        onReviewBrowserJob={(id) => {
          if (!contentVisibleNow.current) return;
          setReviewBrowserJob({ id, viewEpoch: fence.current.capture() });
        }}
        onReviewConnectorIntent={(id) => {
          if (!contentVisibleNow.current) return;
          setReviewConnectorIntent({ id, viewEpoch: fence.current.capture() });
        }}
        onReviewProposal={(id) => {
          if (!contentVisibleNow.current) return;
          const epoch = fence.current.capture();
          void reload().then((current) => {
            if (!current || !fence.current.accepts(epoch)) return;
            if (current.some((proposal) => proposal.id === id)) {
              setReviewProposal(id);
            } else {
              setReviewProposal(null);
              setNotice(
                t(
                  "This draft is no longer awaiting review. It may have been handled or expired; reopen the work task to inspect its saved result.",
                  "此草稿已不再等待审阅，可能已处理或到期。请重新打开工作任务查看保存结果。",
                ),
              );
            }
          });
        }}
      />
      <BrowserWorkflowPanel
        t={t}
        visibleOverride={!displayConcealed}
        reviewEffectId={
          contextVisible &&
          reviewBrowserJob &&
          fence.current.accepts(reviewBrowserJob.viewEpoch)
            ? reviewBrowserJob.id
            : null
        }
        onReviewClosed={() => setReviewBrowserJob(null)}
      />
      <RoutinesPanel t={t} visibleOverride={contextVisible} />
      <ResponsibilitiesPanel
        t={t}
        visibleOverride={!displayConcealed}
        onCompile={(goal) => {
          if (!contentVisibleNow.current) return;
          setWorkGoal({ ...goal, viewEpoch: fence.current.capture() });
        }}
      />
      <ConnectorReviewPanel
        t={t}
        visibleOverride={!displayConcealed}
        reviewIntentId={
          contextVisible &&
          reviewConnectorIntent &&
          fence.current.accepts(reviewConnectorIntent.viewEpoch)
            ? reviewConnectorIntent.id
            : null
        }
        onReviewClosed={() => setReviewConnectorIntent(null)}
      />
      <ComputerJobsPanel t={t} taskId={taskId} />
    </div>
  );
}
