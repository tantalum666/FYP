import { errorText } from "../../api";
import type { Translate } from "../../types";
import type { PrivateMutation } from "./usePrivateMutation";
export function MutationFeedback({
  mutation,
  t,
}: {
  mutation: PrivateMutation;
  t: Translate;
}) {
  return (
    <>
      {!!mutation.error && (
        <p className="error-message" role="alert">
          {errorText(mutation.error, t)}
        </p>
      )}
      {mutation.pending && (
        <div className="personal-recovery" role="status">
          <p>
            {t(
              "The result is unknown. Review the saved records before retrying this exact request. The retry is kept only while this panel stays open; after closing or reloading, check the result instead of repeating the action.",
              "结果尚不确定。请先核对保存记录，再重试同一请求。重试资料只在此面板打开期间保留；关闭或刷新后应先核验结果，不要重复操作。",
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
