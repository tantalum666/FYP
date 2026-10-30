import type { Translate } from "../../types";
import { agentError } from "./labels";
export function RequestFeedback({
  mutation,
  t,
}: {
  mutation: {
    error: unknown;
    busy: boolean;
    pending: boolean;
    retry: () => Promise<unknown>;
  };
  t: Translate;
}) {
  return (
    <>
      {!!mutation.error && (
        <p className="error-message" role="alert">
          {agentError(mutation.error, t)}
        </p>
      )}
      {mutation.pending && (
        <div className="agent-notice" role="status">
          <p>
            {t(
              "The response is unknown. Inspect saved records before retrying this exact request. Recovery is held only in this open panel; after closing or reloading, check the result instead of repeating it.",
              "回执未知。请先核对保存记录，再重试同一请求。恢复资料仅在此面板打开期间保留；关闭或刷新后，请先核验结果，不要重复操作。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={mutation.busy}
            onClick={() => void mutation.retry()}
          >
            {t("Retry the same request", "重试同一请求")}
          </button>
        </div>
      )}
    </>
  );
}
