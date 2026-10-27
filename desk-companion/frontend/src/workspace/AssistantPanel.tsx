import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Send, Sparkles } from "lucide-react";
import { ApiError, errorText, request, write } from "../api";
import type { EventInput, Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { VoiceAudio } from "./audio";
import { useDraftGuard } from "../components/DraftGuard";
import type { Task, TaskInput } from "./taskTypes";
import { apiOrigin } from "../native";
import { DateTime } from "luxon";
import { ComputerJobsPanel } from "./ComputerJobsPanel";
import { ToolActivity, type ToolCall } from "./ToolActivity";

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
  plan?: string;
  proposal?: Proposal;
}

export function AssistantPanel({
  t,
  taskId,
}: {
  t: Translate;
  taskId?: string;
}) {
  const { data, refresh } = useWorkspace();
  const [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [reply, setReply] = useState<Reply | null>(null),
    [proposals, setProposals] = useState<Proposal[]>([]),
    [calls, setCalls] = useState<ToolCall[] | null>(null),
    [notice, setNotice] = useState("");
  const [voiceState, setVoiceState] = useState("idle"),
    [transcript, setTranscript] = useState("");
  const audio = useRef<VoiceAudio | null>(null),
    alive = useRef(true);
  const speechText = useRef({ user: "", assistant: "" });
  const knownProposals = useRef<Proposal[]>([]);
  const language = t("en", "zh");
  const ownerView = data?.principal.kind === "owner";
  useDraftGuard(!!text.trim(), busy);
  const reload = useCallback(async () => {
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
      if (alive.current) setError(e);
    }
  }, [language, ownerView]);
  useEffect(() => {
    alive.current = true;
    void reload();
    const timer = setInterval(() => void reload(), 2000);
    return () => {
      alive.current = false;
      clearInterval(timer);
      audio.current?.close();
    };
  }, [reload]);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      setReply(
        await write<Reply>("/assistant/messages", {
          message: text,
          language,
          task_id: taskId ?? null,
        }),
      );
      await reload();
      window.dispatchEvent(new Event("desk:jobs"));
      setText("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function decide(id: string, action: "confirm" | "cancel") {
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
    setError(null);
    setVoiceState("connecting");
    setTranscript("");
    speechText.current = { user: "", assistant: "" };
    try {
      const engine = new VoiceAudio((event) => {
        if (!alive.current) return;
        if (event.type === "ready") setVoiceState("listening");
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
          setNotice(
            t(
              "Voice could not continue. Check the connection or provider configuration.",
              "语音未能继续，请检查连接或服务配置。",
            ),
          );
          setVoiceState("idle");
        }
        if (event.type === "closed" || event.type === "ended")
          setVoiceState("idle");
      });
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
            disabled={!data?.voice.configured}
            onClick={() => void startVoice()}
          >
            <Mic size={18} />
            {t("Start conversation", "开始交谈")}
          </button>
        ) : (
          <button
            className="secondary"
            onClick={() => {
              audio.current?.close();
              setVoiceState("idle");
            }}
          >
            <MicOff size={18} />
            {t("End conversation", "结束交谈")}
          </button>
        )}
      </div>
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
        </>
      )}
      {transcript && (
        <p className="assistant-reply" aria-live="polite">
          {transcript}
        </p>
      )}
      <form onSubmit={send}>
        <label className="field">
          {t("Your request", "你的要求")}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
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
          <button className="primary" disabled={busy || !text.trim()}>
            <Send size={16} />
            {busy ? t("Preparing…", "处理中…") : t("Send", "发送")}
          </button>
          {!taskId && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => setText(t("What is on today?", "今天的行程"))}
            >
              {t("Today’s briefing", "今日简报")}
            </button>
          )}
        </div>
      </form>
      <ToolActivity t={t} calls={calls} />
      <p className="workspace-hint">
        {data?.text_ai?.configured
          ? t(
              "AI text is connected to your configured provider. Confirm drafts before they change anything.",
              "文字AI使用已配置的服务；草稿需确认后才会修改记录。",
            )
          : t(
              "Local rules: Remember: a fact, Save note: text, or Track: report. Confirm before anything is stored. AI voice is a separate connection.",
              "本地规则：用“记住：一条事实”、“保存笔记：文本”或“跟进：报告”。确认后才会保存。AI语音单独连接。",
            )}
      </p>
      {reply && (
        <div className="assistant-reply" role="status">
          <p>{reply.message}</p>
          {reply.plan ? <p className="assistant-plan">{reply.plan}</p> : null}
        </div>
      )}
      {proposals.map((p) => {
        const event = p.data.event ?? p.data.change?.event;
        const task = p.data.task ?? p.data.change?.task ?? p.data.original_task;
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
                        : t("May appear on the desk display", "可在常亮屏展示")}
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
                      {p.data.original.title || t("Private event", "私人事项")}
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
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      <ComputerJobsPanel t={t} taskId={taskId} />
    </div>
  );
}
