import { useEffect, useState } from "react";
import { request } from "../../api";
import type { Translate } from "../../types";
import type { Task, TaskEvidence } from "../taskTypes";
import type { ResponseFence } from "../personal/responseFence";
import { watchError } from "./labels";
export function CurrentTask({
  id,
  fence,
  epoch,
  fresh,
  t,
  close,
  onAccessDenied,
}: {
  id: string;
  fence: ResponseFence;
  epoch: number;
  fresh: boolean;
  t: Translate;
  close: () => void;
  onAccessDenied: (reason: unknown) => void;
}) {
  const [value, setValue] = useState<{
    task: Task;
    evidence: TaskEvidence[];
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let live = true;
    setValue(null);
    setError(null);
    if (fresh && fence.accepts(epoch))
      void request<{ task: Task; evidence: TaskEvidence[] }>(
        `/tasks/${encodeURIComponent(id)}`,
      )
        .then((next) => {
          if (!live || !fence.accepts(epoch)) return;
          if (next.task.redacted) {
            setValue(null);
            fence.update(`source-redacted:${crypto.randomUUID()}`, false);
            onAccessDenied({ code: "PRIVATE_CONTEXT_HIDDEN", status: 403 });
          } else if (next.task.id === id) setValue(next);
        })
        .catch((reason) => {
          if (!live || !fence.accepts(epoch)) return;
          if (
            reason &&
            typeof reason === "object" &&
            "code" in reason &&
            /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN|CONTEXT_CHANGED/.test(
              String(reason.code),
            )
          ) {
            setValue(null);
            fence.update(`source-denied:${crypto.randomUUID()}`, false);
            onAccessDenied(reason);
          } else setError(reason);
        });
    return () => {
      live = false;
    };
  }, [id, fence, epoch, fresh]);
  if (!fresh || !fence.accepts(epoch)) return null;
  return (
    <section className="watch-review">
      <h4>{t("Current saved task", "当前保存的事务")}</h4>
      <button type="button" className="text-button" onClick={close}>
        {t("Close current record", "关闭当前记录")}
      </button>
      {!!error && <p role="alert">{watchError(error, t)}</p>}
      {value && (
        <>
          <strong>{value.task.title}</strong>
          <p>
            {id} · v{value.task.version} · {value.task.updated_at}
          </p>
          <p>
            {t("Status", "状态")}:{" "}
            {
              {
                todo: t("To do", "待处理"),
                in_progress: t("In progress", "进行中"),
                waiting: t("Waiting", "等待中"),
                completed: t("Completed", "已完成"),
                cancelled: t("Cancelled", "已取消"),
              }[value.task.status]
            }
          </p>
          <p>
            {t("Due", "截止")}: {value.task.due_local ?? t("None", "无")} ·{" "}
            {value.task.timezone}
          </p>
          <p>{value.task.next_step}</p>
          <p>{value.task.waiting_for}</p>
          <ul>
            {value.task.steps.map((step, i) => (
              <li key={i}>
                {step.done ? "✓ " : ""}
                {step.title}
              </li>
            ))}
          </ul>
          <ul>
            {value.evidence
              .filter((item) => item.kind === "note")
              .map((item) => (
                <li key={item.id}>
                  {item.at}: {item.note}
                </li>
              ))}
          </ul>
          <small>
            {t(
              "Live read of current saved values, not the values when the review was first observed.",
              "当前保存数值的实时读取，不代表首次观察变化时的数值。",
            )}
          </small>
        </>
      )}
    </section>
  );
}
