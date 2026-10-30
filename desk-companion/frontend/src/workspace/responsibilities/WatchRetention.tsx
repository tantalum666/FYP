import type { Translate } from "../../types";
import { useDraftGuard } from "../../components/DraftGuard";
import type { ResponseFence } from "../personal/responseFence";
import { fieldLabel, statusLabel, watchError } from "./labels";
import { terminalWatch, validMaintenanceUsage } from "./retention";
import type {
  RetentionAction,
  RetentionPreview,
  WatchMaintenanceUsage,
  WatchMutationResult,
} from "./retention";
import type { Responsibility } from "./types";
import { useWatchRetention } from "./useWatchRetention";
export function retentionLabel(action: RetentionAction, t: Translate) {
  return action === "trash"
    ? t("Move to Trash", "移到废纸篓")
    : action === "restore"
      ? t("Restore history", "恢复历史")
      : t("Permanently remove", "永久移除");
}
export function WatchUsage({
  usage,
  limit,
  t,
}: {
  usage: WatchMaintenanceUsage | undefined;
  limit: number | undefined;
  t: Translate;
}) {
  const valid = validMaintenanceUsage(usage) ? usage : null;
  const retained = valid?.retained_count ?? null;
  const knownLimit = Number.isSafeInteger(limit) && limit! > 0 ? limit! : null;
  return (
    <div className="watch-usage">
      <p>
        {t("Saved watch slots, including Trash", "保存的关注位置（含废纸篓）")}:{" "}
        {retained ?? t("Unknown usage", "用量未知")}/
        {knownLimit ?? t("Unknown limit", "上限未知")}
        {retained !== null && knownLimit !== null && (
          <>
            {" "}
            · {Math.max(0, knownLimit - retained)}{" "}
            {t("slots remaining", "剩余位置")}
          </>
        )}
      </p>
      <p>
        {t("Lifetime watch identities", "存储生命周期内的关注标识")}:{" "}
        {valid?.lifetime_count ?? t("Unknown usage", "用量未知")}/
        {valid?.lifetime_limit ?? t("Unknown limit", "上限未知")}
        {valid?.lifetime_remaining !== null &&
          valid?.lifetime_remaining !== undefined && (
            <>
              {" "}
              · {valid.lifetime_remaining}{" "}
              {t("new identities remaining", "剩余新标识")}
            </>
          )}
      </p>
      <small>
        {t(
          "Trash and cancelled history still use a saved-watch slot. Permanent removal releases one saved slot but keeps its lifetime identity and opaque retry receipts. The lifetime limit is 256; cleanup cannot reset it. Unknown usage is not free space.",
          "废纸篓及已取消历史仍占保存位置。永久移除释放一个保存位置，但保留生命周期标识和不含正文的重试回执。生命周期上限为256，清理不会重置；未知用量不代表空余容量。",
        )}
      </small>
    </div>
  );
}
/** Separate confirmation body; the only purge caller passes strict true from its final owner button. */
export function RetentionConfirmation({
  preview,
  t,
  disabled,
  onConfirm,
  onCancel,
}: {
  preview: RetentionPreview;
  t: Translate;
  disabled: boolean;
  onConfirm: (permanent: boolean) => void;
  onCancel: () => void;
}) {
  const purge = preview.action === "purge";
  return (
    <section
      className={`watch-retention-confirm ${purge ? "irreversible" : ""}`}
      role="alertdialog"
      aria-modal="false"
      aria-labelledby="watch-retention-heading"
    >
      <h3 id="watch-retention-heading">
        {purge
          ? t("Confirm permanent removal", "确认永久移除")
          : retentionLabel(preview.action, t)}
      </h3>
      <strong>{preview.responsibility.title}</strong>
      <p>
        {t("Exact watch ID", "确切关注ID")}: {preview.responsibility.id}
      </p>
      <p>
        {t("Watch version", "关注版本")}: {preview.responsibility.version} ·{" "}
        {t("Retention version", "留存版本")}:{" "}
        {preview.responsibility.retention_version}
      </p>
      <ul>
        <li>
          {t("Watch definition", "关注定义")}: {preview.counts.definitions}
        </li>
        <li>
          {t("Source baselines", "来源基线")}: {preview.counts.source_baselines}
        </li>
        <li>
          {t("Saved change reviews", "保存的变化审阅")}:{" "}
          {preview.counts.retained_reviews}
        </li>
        <li>
          {t(
            "Opaque operation receipts retained afterward",
            "操作后保留的不含正文回执",
          )}
          : {preview.retained_operation_receipts_after}
        </li>
        <li>
          {t("Logical saved-watch slots released", "释放的逻辑保存位置")}:{" "}
          {preview.logical_slots_released}
        </li>
      </ul>
      <p>
        {purge
          ? t(
              "This permanently removes this watch's title, selected-source baselines and saved review history. Normal product recovery cannot undo it. Opaque ID, lifecycle metadata and operation hashes/references remain to prevent old retries from recreating it.",
              "这将永久移除此关注的标题、所选来源基线和保存的审阅历史，无法通过正常产品恢复撤销。不含正文的ID、留存元数据及操作哈希／引用仍保留，防止旧重试重新创建。",
            )
          : preview.action === "restore"
            ? t(
                "Restore makes this same terminal history visible again. It never resumes the watch, resets spent budgets or creates Work. No slot is released.",
                "恢复只让同一已终止历史重新可见，不会重新开始关注、重置已用额度或创建工作，也不释放位置。",
              )
            : t(
                "Trash hides this terminal history from the ordinary list. The same history can be restored; its saved-watch slot is still used. No slot is released.",
                "移到废纸篓会从普通列表隐藏此已终止历史，可恢复同一历史，仍占保存位置，不释放容量。",
              )}
      </p>
      <p>
        {t(
          "Watched tasks and independently started Work stay untouched. No automatic cleanup, restart, notification or new work.",
          "被关注事务及独立开始的工作保持不变，不会自动清理、重新开始、通知或新建工作。",
        )}
      </p>
      {purge && (
        <p>
          {t(
            "This does not erase backups, downloaded copies or provider copies, and does not promise forensic erasure or a smaller database file.",
            "这不会擦除备份、已下载副本或提供商副本，也不承诺法证擦除或缩小数据库文件。",
          )}
        </p>
      )}
      <small>
        {t("Preview expires", "预览到期")}: {preview.expires_at} ·{" "}
        {t(
          "Current identity, privacy and exact inventory must still match.",
          "当前身份、隐私及确切记录清单仍须匹配。",
        )}
      </small>
      <div className="workspace-inline-actions">
        <button
          type="button"
          className={purge ? "danger" : "primary"}
          disabled={disabled}
          onClick={() => onConfirm(purge)}
        >
          {purge
            ? t("Permanently remove this exact history", "永久移除此确切历史")
            : retentionLabel(preview.action, t)}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={disabled}
          onClick={onCancel}
        >
          {t("Cancel, keep unchanged", "取消并保持不变")}
        </button>
      </div>
    </section>
  );
}
export function WatchRetention({
  fence,
  epoch,
  fresh,
  revision,
  rows,
  limit,
  t,
  onChanged,
  onDenied,
  onClose,
}: {
  fence: ResponseFence;
  epoch: number;
  fresh: boolean;
  revision: number | undefined;
  rows: Responsibility[];
  limit: number | undefined;
  t: Translate;
  onChanged: (result: WatchMutationResult) => void;
  onDenied: (error: unknown) => void;
  onClose: () => void;
}) {
  const state = useWatchRetention(
    fence,
    epoch,
    fresh,
    revision,
    onChanged,
    onDenied,
  );
  useDraftGuard(!!state.preview || state.pending, state.busy);
  const locked =
    !state.available || state.loading || state.busy || state.pending;
  const row = state.detail?.responsibility;
  return (
    <section
      className="watch-maintenance"
      aria-label={t("Watch history and Trash", "关注历史与废纸篓")}
    >
      <h3>{t("Watch history and Trash", "关注历史与废纸篓")}</h3>
      <p>
        {t(
          "Only cancelled, expired or budget-exhausted watches can be maintained. Cancel an active, paused or blocked watch first using its existing controls.",
          "仅可整理已取消、已到期或总额度耗尽的关注。关注中、已暂停或受阻的关注需先使用原有控制取消。",
        )}
      </p>
      <div className="workspace-inline-actions">
        <button
          type="button"
          className="secondary"
          disabled={!state.available || state.busy || state.loading}
          onClick={() => void state.refresh()}
        >
          {t("Refresh history and Trash", "刷新历史与废纸篓")}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={state.busy || state.pending || !!state.preview}
          onClick={onClose}
        >
          {t("Close history maintenance", "关闭历史整理")}
        </button>
      </div>
      {!state.available && (
        <p role="status">
          {t(
            "Waiting for current owner access and records. Confirmations are disabled.",
            "等待当前本人访问权限和记录，确认操作已停用。",
          )}
        </p>
      )}
      {!!state.error && <p role="alert">{watchError(state.error, t)}</p>}
      {state.pending && (
        <div role="status" className="watch-review">
          <p>
            {t(
              "The result is unknown. Refresh and inspect current history, then retry only this original request. The original body and operation ID remain in this authorized open view, even after preview expiry. Closing or changing privacy clears them; inspect actual state before any new action.",
              "结果未知。先刷新并查看当前历史，再仅重试此原始请求。原正文和操作ID保留在此获授权的打开视图，即使预览到期也不会更换。关闭或隐私变化会清除，请在任何新操作前查看实际状态。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={!state.available || state.busy}
            onClick={state.retry}
          >
            {t("Retry original maintenance request", "重试原始历史整理请求")}
          </button>
        </div>
      )}
      {state.result && (
        <p role="status">
          {"kind" in state.result
            ? state.result.retention_state === "purged"
              ? t(
                  "Recorded operation recovered or saved. This exact history is now permanently removed; its opaque retry metadata remains. Refresh usage to see current capacity.",
                  "操作已恢复回执或保存。此确切历史现已永久移除，不含正文的重试元数据仍保留。请刷新用量查看当前容量。",
                )
              : t(
                  "Recorded operation recovered or saved. This history is currently in Trash and still uses one saved-watch slot.",
                  "操作已恢复回执或保存。此历史当前在废纸篓，仍占一个保存位置。",
                )
            : t(
                "History restored or an earlier recorded operation recovered. Its current status is terminal; it has not resumed.",
                "历史已恢复或已找回先前操作回执。当前状态仍为已终止，不会重新开始。",
              )}
        </p>
      )}
      {state.list && (
        <>
          <WatchUsage
            usage={state.list.maintenance_usage}
            limit={limit}
            t={t}
          />
          <h4>{t("Terminal history", "已终止历史")}</h4>
          {rows
            .filter((r) => terminalWatch(r.status))
            .map((r) => (
              <button
                type="button"
                className="secondary watch-maintenance-row"
                disabled={
                  !state.available ||
                  state.loading ||
                  state.busy ||
                  !!state.preview
                }
                key={r.id}
                onClick={() => void state.inspect(r.id)}
              >
                {r.title} · {r.id} · {statusLabel(r.status, t)}
              </button>
            ))}
          <h4>
            {t("Trash", "废纸篓")} (
            {state.list.maintenance_usage.trashed_count ?? t("Unknown", "未知")}
            )
          </h4>
          {!state.list.responsibilities.length && (
            <p>{t("No history shown in Trash.", "废纸篓暂无可显示历史。")}</p>
          )}
          {state.list.responsibilities.map((r) => (
            <button
              type="button"
              className="secondary watch-maintenance-row"
              disabled={
                !state.available ||
                state.loading ||
                state.busy ||
                !!state.preview
              }
              key={r.id}
              onClick={() => void state.inspect(r.id)}
            >
              {r.title} · {r.id} · {statusLabel(r.status, t)}
            </button>
          ))}
        </>
      )}
      {row && !state.preview && (
        <section className="watch-review">
          <h4>{row.title}</h4>
          <p>
            {row.id} · {statusLabel(row.status, t)} ·{" "}
            {row.retention_state === "trashed"
              ? t("In Trash", "在废纸篓")
              : t("Retained history", "保留历史")}
          </p>
          <p>
            {t("Spent review budget remains", "已用审阅额度保持")}:{" "}
            {row.reviews_used}/{row.review_budget}
          </p>
          <ul>
            {state.detail!.reviews.map((review) => (
              <li key={review.id}>
                {statusLabel(review.delivery_state, t)} · {review.id} ·{" "}
                {review.changed_fields.map((f) => fieldLabel(f, t)).join(" · ")}
              </li>
            ))}
          </ul>
          <div className="workspace-inline-actions">
            {(row.retention_state === "trashed"
              ? ["restore", "purge"]
              : ["trash", "purge"]
            ).map((action) => (
              <button
                type="button"
                className="secondary"
                disabled={locked}
                key={action}
                onClick={() =>
                  void state.prepare(row, action as RetentionAction)
                }
              >
                {t("Preview", "预览")} ·{" "}
                {retentionLabel(action as RetentionAction, t)}
              </button>
            ))}
          </div>
        </section>
      )}
      {state.preview && (
        <RetentionConfirmation
          key={state.preview.preview_id}
          preview={state.preview}
          t={t}
          disabled={locked}
          onConfirm={(permanent) => state.confirm(state.preview!, permanent)}
          onCancel={state.cancel}
        />
      )}
    </section>
  );
}
