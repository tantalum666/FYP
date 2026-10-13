import type { Translate } from "../../types";
import { browserState } from "../browser/labels";
import { browserExportVerified, browserVerified } from "../browser/types";
import type { BrowserJob } from "../browser/types";

export function RunBrowserJobs({
  jobs,
  t,
  locked,
  onReview,
}: {
  jobs: BrowserJob[];
  t: Translate;
  locked: boolean;
  onReview?: (id: string) => void;
}) {
  if (!jobs.length) return null;
  return (
    <section>
      <h4>{t("Linked browser work", "关联浏览器工作")}</h4>
      <p className="workspace-hint">
        {t(
          "Each browser edit has its own exact-content approval. The run continues from the recorded result after review; opening the review does not approve or replay an action.",
          "每项浏览器编辑均需单独批准确切内容。审阅后运行会根据记录结果继续；打开审阅不会批准或重放操作。",
        )}
      </p>
      {jobs.map((job) => (
        <article className="agent-review" key={job.id}>
          <strong>
            {job.request?.title || t("Public browser brief", "公开浏览器简报")}
          </strong>
          <p role="status">{browserState(job.state, t)}</p>
          <small>
            {job.id} · v{job.version}
          </small>
          {job.request && (
            <small>
              {t("Destination", "目的地")}: {job.request.destination}
            </small>
          )}
          {browserExportVerified(job) && (
            <p>
              {t("Export bytes independently read back", "导出字节已独立读回")}{" "}
              · {job.result!.byte_count} {t("bytes", "字节")}
            </p>
          )}
          {browserExportVerified(job) && !browserVerified(job) && (
            <p className="agent-notice">
              {t(
                "Export bytes exist, but execution or cleanup remains uncertain. This is not verified browser completion.",
                "导出字节已存在，但执行或清理仍不确定。这不代表浏览器工作已核验完成。",
              )}
            </p>
          )}
          {job.state === "unknown" && (
            <p className="workspace-hint">
              {t(
                "Inspect existing evidence and use read-only verification. Do not repeat the edit to guess at completion.",
                "请检查已有证据并使用只读核验，不要重复编辑来猜测是否完成。",
              )}
            </p>
          )}
          <button
            type="button"
            className="secondary"
            disabled={locked || !onReview}
            onClick={() => onReview?.(job.id)}
          >
            {t("Open browser review and result", "打开浏览器审阅与结果")}
          </button>
        </article>
      ))}
    </section>
  );
}
