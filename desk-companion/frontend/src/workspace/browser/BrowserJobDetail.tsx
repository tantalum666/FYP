import type { Translate } from "../../types";
import { browserState } from "./labels";
import {
  browserCancellable,
  browserReviewable,
  browserVerified,
  browserExportVerified,
} from "./types";
import type { BrowserJob } from "./types";

export function BrowserJobDetail({
  job,
  t,
  visible,
  ready,
  fresh,
  locked,
  checking,
  cancelling,
  now,
  onApprove,
  onCancel,
  onVerify,
  onDownload,
}: {
  job: BrowserJob;
  t: Translate;
  visible: boolean;
  ready: boolean;
  fresh: boolean;
  locked: boolean;
  checking: boolean;
  cancelling: boolean;
  now: number;
  onApprove: () => void;
  onCancel: () => void;
  onVerify: () => void;
  onDownload: () => void;
}) {
  const verified = visible && browserExportVerified(job);
  const completed = visible && browserVerified(job);
  return (
    <article
      className="browser-job-detail"
      aria-label={t("Browser job review", "浏览器作业核对")}
    >
      <p className="workspace-eyebrow" role="status">
        {browserState(job.state, t)}
      </p>
      <h3>
        {visible
          ? (job.request?.title ??
            t("Saved browser workflow", "已保存的浏览器流程"))
          : t("Private browser job", "私人浏览器作业")}
      </h3>
      <small>
        {t("Job", "作业")} {job.id} · v{job.version}
      </small>
      {visible && job.request && (
        <>
          <dl className="browser-facts">
            <dt>{t("Exact destination", "确切目标")}</dt>
            <dd>{job.request.destination}</dd>
            <dt>{t("Title", "标题")}</dt>
            <dd>{job.request.title}</dd>
            <dt>{t("Document name", "文档名称")}</dt>
            <dd>{job.request.document_name}</dd>
            <dt>{t("Source observed", "已观察来源")}</dt>
            <dd>
              {job.request.source.title}
              <br />
              {job.request.source.url}
              <br />
              <time>{job.request.source.observed_at}</time>
            </dd>
            <dt>{t("Adapter / catalog", "适配器／目录")}</dt>
            <dd>
              {job.request.adapter} / v{job.request.catalog_version}
            </dd>
            <dt>{t("Environment identity", "运行环境身份")}</dt>
            <dd>
              <code>{job.request.environment_id}</code>
            </dd>
          </dl>
          <details open={job.state === "review"}>
            <summary>
              {t("Exact text to enter and export", "将输入并导出的完整文字")}
            </summary>
            <pre tabIndex={0}>{job.request.content}</pre>
          </details>
          <div className="browser-digest">
            {t("Exact intent SHA-256", "确切意图 SHA-256")}
            <code>{job.intent_hash}</code>
          </div>
          {job.state === "review" && (
            <p>
              {t("Review valid until ", "核对有效至 ")}
              <time>{job.expires_at}</time>
            </p>
          )}
        </>
      )}
      {!visible && (
        <p>
          {t(
            "Content and approval are hidden. Cancellation is still available when the owner connection is current.",
            "内容与批准已隐藏，拥有者连接有效时仍可请求取消。",
          )}
        </p>
      )}
      {job.state === "review" && visible && (
        <p className="workspace-hint">
          {t(
            "Approval allows this exact public/synthetic text to be entered into StackEdit and exported once. The clean editor session is temporary; only the verified export is retained. This does not publish or sync a document.",
            "批准后会将这份确切的公开／虚构文字输入 StackEdit 并导出一次。独立编辑器会话为临时会话，仅核验后的导出会保留；不会发布或同步文档。",
          )}
        </p>
      )}
      {job.state === "unknown" && (
        <p className="browser-warning" role="status">
          {t(
            "An edit or export may already exist. Verification only reads the existing result; it never repeats the editor action.",
            "编辑或导出可能已产生。核验只读取已有结果，不会重复编辑器动作。",
          )}
        </p>
      )}
      {job.cancel_requested && (
        <p>
          {t(
            "Stopping does not undo a completed edit or remove an export.",
            "停止不会撤销已完成的编辑或删除导出。",
          )}
        </p>
      )}
      {visible && job.error && (
        <p className="browser-warning">
          {t("Recorded reason: ", "记录原因：")}
          <code>{job.error}</code>
        </p>
      )}
      {verified && (
        <div className="browser-verification">
          <strong>
            {t("Export bytes independently verified", "导出字节已独立核验")}
          </strong>
          <p>
            {job.result!.byte_count} {t("bytes", "字节")}
          </p>
          <code>SHA-256 {job.result!.sha256}</code>
          <p>
            {t("Browser: ", "浏览器：")}
            {job.result!.browser_version} ·{" "}
            {job.cleanup_confirmed && job.result?.process_cleanup_confirmed
              ? t("Owned process cleanup confirmed", "已确认自有进程清理")
              : t(
                  "Owned process cleanup is unconfirmed",
                  "尚未确认自有进程清理",
                )}
          </p>
          <p>
            {t(
              "This verifies the exported content, not the truth or quality of the source brief.",
              "这证明导出内容一致，不代表来源简报的事实或质量已经审查。",
            )}
          </p>
        </div>
      )}
      {visible && job.state === "succeeded" && !completed && (
        <p role="alert">
          {t(
            "Verification evidence is missing or incomplete. Do not treat this as verified success.",
            "缺少完整核验证据，不应视为已核验成功。",
          )}
        </p>
      )}
      {!!job.history?.length && (
        <details>
          <summary>{t("Recorded progress", "已记录进展")}</summary>
          <ol className="browser-progress">
            {job.history.slice(-12).map((event, index) => (
              <li key={`${event.at}:${index}`}>
                <time>{event.at}</time> · {browserState(event.state, t)}
                {visible && event.code && <code> · {event.code}</code>}
              </li>
            ))}
          </ol>
          {job.history.length > 12 && (
            <small>
              {t(
                "Showing the latest 12 transitions.",
                "显示最近12次状态变化。",
              )}
            </small>
          )}
        </details>
      )}
      <div className="workspace-inline-actions">
        {job.state === "review" && visible && (
          <button
            className="primary"
            type="button"
            disabled={locked || !browserReviewable(job, ready && fresh, now)}
            onClick={onApprove}
          >
            {t("Approve this exact edit and export", "批准此确切编辑与导出")}
          </button>
        )}
        {browserCancellable(job) && (
          <button
            className="secondary"
            type="button"
            disabled={cancelling || !fresh}
            onClick={onCancel}
          >
            {t("Cancel browser job", "取消浏览器作业")}
          </button>
        )}
        {visible && ["unknown", "succeeded"].includes(job.state) && (
          <button
            className="secondary"
            type="button"
            disabled={checking || !fresh}
            onClick={onVerify}
          >
            {t("Read-only verification", "只读核验")}
          </button>
        )}
        {verified && (
          <button
            className="secondary"
            type="button"
            disabled={checking || !fresh}
            onClick={onDownload}
          >
            {t("Download verified Markdown", "下载已核验 Markdown")}
          </button>
        )}
      </div>
    </article>
  );
}
