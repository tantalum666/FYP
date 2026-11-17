import { useEffect, useState } from "react";
import { Check, Clock3, Sparkles, X } from "lucide-react";
import { errorText, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import "./alice-checkin.css";

export interface AliceCue {
  id: string;
  kind: "posture" | "task" | "morning_brief" | "evening_check" | "initiative";
  message_en?: string;
  message_zh?: string;
  position?: string;
  outcome?: string;
  task_id?: string;
  version?: number;
  title?: string;
  next_step?: string;
  waiting_for?: string;
  status?: string;
  open_count?: number;
  tasks?: Array<{ title: string; due_at: string | null }>;
}

/** One small cue beside Alice; no background model call or notification wall. */
export function AliceCheckIn({
  t,
  visible,
}: {
  t: Translate;
  visible: boolean;
}) {
  const { data, offline, stale, refresh } = useWorkspace();
  const cue = data?.check_in;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [feedback, setFeedback] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [hidden, setHidden] = useState<string[]>([]);
  useEffect(() => {
    setExpanded(false);
    setError(null);
  }, [cue?.id]);
  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(""), 10000);
    return () => clearTimeout(timer);
  }, [feedback]);
  if (
    !visible ||
    offline ||
    stale ||
    !data?.personal_context_visible ||
    data.principal.kind !== "owner"
  )
    return null;
  if (feedback)
    return (
      <aside className="alice-checkin" role="status">
        <Check size={16} />
        <p>{feedback}</p>
      </aside>
    );
  if (!cue || hidden.includes(cue.id)) return null;
  async function act(action: "complete" | "continue" | "snooze" | "dismiss") {
    if (!cue || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (cue.kind === "task") {
        await write(`/tasks/${cue.task_id}/actions`, {
          expected_version: cue.version,
          ...(action === "complete"
            ? { action: "complete" }
            : action === "continue"
              ? {
                  action: "note",
                  note: t(
                    "Still in progress; continuing the next step.",
                    "尚未完成，继续推进下一步。",
                  ),
                }
              : { action: "snooze", minutes: 60 }),
        });
        const next = data?.tasks.preview?.find(
          (task) => task.id !== cue.task_id && !task.paused && !task.redacted,
        );
        setFeedback(
          action === "complete"
            ? next
              ? t(
                  `Done — I've recorded that. Next, you could look at “${next.title}”.`,
                  `已记录完成。接下来可以看看「${next.title}」。`,
                )
              : t(
                  "Done — I've recorded that. Take a moment before the next thing.",
                  "已经记录完成了。缓一缓，再继续下一件。",
                )
            : action === "continue"
              ? cue.next_step ||
                t(
                  "Start with one small step. We can check in again later.",
                  "先推进一个小步骤，我们稍后再跟进。",
                )
              : t("I'll check back in an hour.", "一小时后再跟你确认。"),
        );
      } else if (cue.kind === "initiative") {
        await write(`/initiative/${cue.id}/dismissals`, {});
      } else if (cue.kind === "posture") {
        await write("/posture/actions", { action: "snooze", minutes: 10 });
      } else await write(`/nudges/${cue.id}/dismissals`, {});
      setHidden((ids) => [...ids.slice(-19), cue.id]);
      await refresh();
    } catch (failure) {
      setError(failure);
      await refresh();
    } finally {
      setBusy(false);
    }
  }
  const text =
    cue.kind === "initiative"
      ? t(cue.message_en ?? "", cue.message_zh ?? "")
      : cue.kind === "task"
        ? cue.status === "waiting"
          ? t(
              `${cue.title}: has what you were waiting for arrived?`,
              `「${cue.title}」等的事情有结果了吗？`,
            )
          : t(
              `How is “${cue.title}” going?`,
              `「${cue.title}」进行得怎么样了？`,
            )
        : cue.kind === "posture"
          ? cue.outcome === "adjusted"
            ? t(
                "That is back within your reference position.",
                "已经回到刚才标定的参考范围了。",
              )
            : cue.position === "movement"
              ? t(
                  "You've been at the desk for a while. Take a short movement break when you can.",
                  "你已经在桌前待了一段时间，方便的话起来活动一下。",
                )
              : cue.position === "forward"
                ? t(
                    "You've been leaning forward for a while. Ease back toward your usual position.",
                    "你已经向前靠了一会儿，试着轻轻回到平时的位置。",
                  )
                : t(
                    "You've been leaning to one side. Try returning toward the centre.",
                    "你已经向一侧偏了一会儿，试着轻轻回到中间。",
                  )
          : cue.open_count
            ? t(
                `You have ${cue.open_count} open item(s). ${cue.tasks?.map((x) => x.title).join("; ") || "Let's choose a next step."}`,
                `手头还有 ${cue.open_count} 件事。${cue.tasks?.map((x) => x.title).join("、") || "可以先选一件推进。"}`,
              )
            : t(
                "Nothing is waiting on your task list. Leave a little room to rest, too.",
                "待办清单里暂时没有未完成事项，也给自己留一点休息时间。",
              );
  return (
    <aside
      className={`alice-checkin ${expanded ? "is-expanded" : ""}`}
      aria-label={t("Alice check-in", "Alice 主动提醒")}
      aria-live="polite"
    >
      <Sparkles size={16} aria-hidden="true" />
      <div>
        <p>{text}</p>
        {cue.kind === "task" && cue.next_step && (
          <small>
            {t("Next: ", "下一步：")}
            {cue.next_step}
          </small>
        )}
        {(text.length > 120 || (cue.next_step?.length ?? 0) > 120) && (
          <button
            className="text-button"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? t("Less", "收起") : t("Details", "详情")}
          </button>
        )}
        <div className="alice-checkin-actions">
          {cue.kind === "task" ? (
            <>
              <button disabled={busy} onClick={() => void act("complete")}>
                <Check size={14} />
                {t("Done", "完成了")}
              </button>
              <button disabled={busy} onClick={() => void act("continue")}>
                {t("Still working", "还在进行")}
              </button>
              <button disabled={busy} onClick={() => void act("snooze")}>
                <Clock3 size={14} />
                {t("In an hour", "一小时后")}
              </button>
            </>
          ) : (
            <button disabled={busy} onClick={() => void act("dismiss")}>
              {cue.kind === "posture"
                ? t("Quiet for 10 minutes", "安静十分钟")
                : t("Got it", "知道了")}
            </button>
          )}
        </div>
        {!!error && <small role="alert">{errorText(error, t)}</small>}
      </div>
      <button
        className="text-button"
        aria-label={t("Hide this reminder", "收起这条提醒")}
        onClick={() => setHidden((ids) => [...ids.slice(-19), cue.id])}
      >
        <X size={15} />
      </button>
    </aside>
  );
}
