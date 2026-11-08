import { DateTime } from "luxon";
import type { Translate } from "../types";
import type { Proposal } from "./assistantTypes";
import { JourneyAdvice } from "./JourneyAdvice";
import { isJourneyAdvice } from "./proposalDecision";

export function ProposalActionCard({
  proposal: p,
  t,
  busy,
  onDecision,
}: {
  proposal: Proposal;
  t: Translate;
  busy: boolean;
  onDecision: (action: "confirm" | "cancel") => void;
}) {
  const language = t("en", "zh");
  const event = p.data.event ?? p.data.change?.event;
  const task = p.data.task ?? p.data.change?.task ?? p.data.original_task;
  const taskAction = p.data.change?.action ?? "create";
  const taskActionLabel =
    (
      {
        create: t("Create task", "创建事务"),
        update: t("Update task details", "更新事务详情"),
        note: t("Save progress note", "保存进展记录"),
        complete: t("Mark complete and stop follow-ups", "标记完成并停止跟进"),
        cancel: t("Cancel task and stop follow-ups", "取消事务并停止跟进"),
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
    p.kind === "memory_delete" ||
    p.kind === "memory_consolidate";
  const journeyKind = isJourneyAdvice(p.kind);
  return (
    <article className="assistant-action-card assistant-proposal">
      <span className="workspace-eyebrow">
        {t("Permission needed", "需要你的允许")}
      </span>
      {p.kind === "email_send" ? (
        <>
          <h3>{t("Send email", "发送邮件")}</h3>
          <p>
            {t("From: ", "发件人：")}
            {p.data.from}
          </p>
          <p>
            {t("To: ", "收件人：")}
            {p.data.to}
          </p>
          <p>
            {t("Subject: ", "主题：")}
            {p.data.subject}
          </p>
          <blockquote style={{ whiteSpace: "pre-wrap" }}>
            {p.data.body}
          </blockquote>
        </>
      ) : journeyKind ? (
        <JourneyAdvice proposal={p} t={t} />
      ) : memoryKind ? (
        <>
          <h3>
            {p.kind === "memory_consolidate"
              ? t("Review duplicate facts", "核对重复事实")
              : p.kind === "memory_delete"
                ? t("Delete a saved fact", "删除一条记忆")
                : p.kind === "memory_replace"
                  ? t("Correct a saved fact", "更正一条记忆")
                  : t("Save a fact", "保存一条记忆")}
          </h3>
          {p.kind === "memory_consolidate" && (
            <>
              <p>{t(p.data.reason_en ?? "", p.data.reason_zh ?? "")}</p>
              <p>
                {t("Keep: ", "保留：")}
                {p.data.keep_body}
              </p>
              {(p.data.retire ?? []).map((row, index) => (
                <p key={index}>
                  {t("Retire: ", "停用：")}
                  {row.body}
                </p>
              ))}
            </>
          )}
          {p.data.previous && (
            <p>
              {t("Current: ", "当前：")}
              {p.data.previous}
            </p>
          )}
          {p.data.body && <blockquote>{p.data.body}</blockquote>}
          <small>
            {t(
              "Confirming adds this to saved memories. A deleted fact is left out of later requests.",
              "确认后会加入已保存记忆。删除后，之后的请求不再包含这条事实。",
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
                {p.data.goal && (
                  <span>
                    {t(
                      " — Goal stays open until you confirm completion.",
                      " — 目标在你确认完成前保持开启。",
                    )}
                  </span>
                )}
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
          onClick={() => onDecision("confirm")}
        >
          {p.kind === "email_send"
            ? t("Send email", "发送邮件")
            : journeyKind
              ? t("Save reviewed update", "保存核对结果")
              : t("Allow once", "允许这一次")}
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => onDecision("cancel")}
        >
          {t("Cancel draft", "取消草稿")}
        </button>
      </div>
    </article>
  );
}
