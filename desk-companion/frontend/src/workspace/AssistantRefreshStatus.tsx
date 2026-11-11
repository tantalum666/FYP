import type { Translate } from "../types";

/** One read-only recovery notice; never retries a business write. */
export function AssistantRefreshStatus({
  reconnecting,
  onRetry,
  t,
}: {
  reconnecting: boolean;
  onRetry: () => void;
  t: Translate;
}) {
  return (
    <div className="assistant-refresh-status" role="status">
      <span>
        {reconnecting
          ? t("Reconnecting…", "正在重新连接…")
          : t("Actions could not refresh", "操作状态暂未更新")}
      </span>
      <button type="button" className="text-button" onClick={onRetry}>
        {t("Retry", "重试")}
      </button>
    </div>
  );
}
