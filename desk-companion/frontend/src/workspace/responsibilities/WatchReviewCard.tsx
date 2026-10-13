import type { Translate } from "../../types";
import type { WatchDetail, WatchReview } from "./types";
import { followupTaskIds } from "./types";
import { fieldLabel, statusLabel } from "./labels";
export function WatchReviewCard({
  review,
  detail,
  t,
  disabled,
  onAcknowledge,
  onCompile,
  onInspect,
}: {
  review: WatchReview;
  detail: WatchDetail;
  t: Translate;
  disabled: boolean;
  onAcknowledge: () => void;
  onCompile: (ids: string[]) => void;
  onInspect: (id: string) => void;
}) {
  const ids = followupTaskIds(detail);
  return (
    <article className="watch-review">
      <h4>{t("Selected task changes", "所选事务有更新")}</h4>
      <p>
        {statusLabel(review.delivery_state, t)} · v{review.version}
      </p>
      <p>
        {t("Observed", "观察时间")}: {review.first_observed_at} →{" "}
        {review.last_observed_at}
      </p>
      <p>
        {review.changed_fields.map((field) => fieldLabel(field, t)).join(" · ")}
      </p>
      <p className="workspace-hint">
        {t(
          "Field names record observed saved changes. Titles and inspected values come from current records, not historical snapshots. Intermediate edits may have coalesced.",
          "字段名称记录已观察到的保存变化。标题和查看的数值来自当前记录，不是历史快照；中间修改可能已合并。",
        )}
      </p>
      <ul>
        {review.changed_ids.map((id) => {
          const task = detail.selected_tasks.find((row) => row.id === id);
          return (
            <li key={id}>
              {task?.available
                ? task.title
                : t("Unavailable task", "不可用事务")}{" "}
              <small>{id}</small>
              {task?.available && (
                <button
                  type="button"
                  className="text-button"
                  disabled={disabled}
                  onClick={() => onInspect(id)}
                >
                  {t("Inspect current task", "查看当前事务")}
                </button>
              )}
            </li>
          );
        })}
      </ul>
      {!ids && (
        <p role="status">
          {t(
            "An enrolled task is unavailable. Compilation is blocked; the selection will not silently shrink.",
            "已关注的事务不可用，不能整理证据；不会自动缩小选择范围。",
          )}
        </p>
      )}
      <div className="workspace-inline-actions">
        {review.delivery_state === "pending" && (
          <button
            type="button"
            className="primary"
            disabled={disabled}
            onClick={onAcknowledge}
          >
            {t("Acknowledge", "已查看")}
          </button>
        )}
        <button
          type="button"
          className="secondary"
          disabled={disabled || !ids}
          onClick={() => {
            if (ids) onCompile(ids);
          }}
        >
          {t("Compile current task evidence", "整理当前事务证据")}
        </button>
      </div>
      <small>
        {t(
          "Opening or compiling does not acknowledge this review. Work needs its own scope review, retention choice and Start; stopping this watch does not stop independently started Work.",
          "打开或整理不会确认已查看。工作仍需独立审阅范围、选择保留并开始；停止关注不会停止独立开始的工作。",
        )}
      </small>
    </article>
  );
}
