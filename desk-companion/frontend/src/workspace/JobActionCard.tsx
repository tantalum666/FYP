import { Check, FileText, LoaderCircle, Hand, Monitor } from "lucide-react";
import { useState } from "react";
import { ApiError, errorText } from "../api";
import type { Translate } from "../types";
import {
  isDesktopAction,
  isFolderAction,
  isApplicationAction,
  jobCancellable,
  jobStateLabel,
  readBackCopy,
  recoveryCopy,
  reviewAvailable,
} from "./jobTypes";
import type { ComputerJob } from "./jobTypes";
import type { JobAction } from "./jobRequests";
import { ApplicationPreview } from "./ApplicationPreview";
import { ExportLink } from "./ExportLink";
import { ComputerScreen } from "./ComputerScreen";

export function JobActionCard({
  job,
  t,
  busy,
  cancelling,
  fresh,
  available,
  onAction,
  compact = true,
  refreshToken,
  onContinue,
}: {
  job: ComputerJob;
  t: Translate;
  busy: boolean;
  cancelling: boolean;
  fresh: boolean;
  available: boolean;
  onAction: (action: JobAction) => void;
  compact?: boolean;
  refreshToken?: number;
  onContinue?: () => void;
}) {
  const [exportError, setExportError] = useState<unknown>(null);
  const application = isApplicationAction(job.action);
  const computer = job.action === "computer_use";
  const step = job.request.step;
  const waiting = [
    "queued",
    "running",
    "verifying",
    "cancel_requested",
  ].includes(job.state);
  const writing = [
    "save_note",
    "save_folder_file",
    "linux_note_preview",
    "application",
  ].includes(job.action);
  const destination = isFolderAction(job.action)
    ? job.request.folder_label
    : isDesktopAction(job.action)
      ? t("Linux workspace notes", "Linux 工作空间笔记")
      : t("Desk Companion notes", "Desk Companion 笔记");
  return (
    <article
      className={`assistant-action-card state-${job.state}`}
      aria-label={job.request.title}
    >
      <header>
        {computer && job.result?.outcome === "needs_owner" ? (
          <Hand size={18} />
        ) : job.state === "succeeded" ? (
          <Check size={18} />
        ) : waiting ? (
          <LoaderCircle size={18} />
        ) : computer ? (
          <Monitor size={18} />
        ) : (
          <FileText size={18} />
        )}
        <div>
          <span className="action-state">
            {job.state === "review"
              ? t("Permission needed", "需要你的允许")
              : computer && job.state === "succeeded"
                ? job.result?.outcome === "needs_owner"
                  ? t("Needs you", "需要你接手")
                  : t("Ready for review", "可以核对了")
                : computer && job.state === "running"
                  ? t("Using the browser", "正在操作浏览器")
                  : jobStateLabel(job.state, t)}
          </span>
          <h4>{job.request.title}</h4>
        </div>
      </header>
      {!application && !computer && (
        <p>
          {writing
            ? t("Save a new file in ", "在以下位置保存新文件：")
            : t("Check the saved file in ", "核验以下位置的已有文件：")}
          {destination}.
        </p>
      )}
      {computer && (
        <p className="computer-use-destination">
          {job.request.start_url?.startsWith("demo:")
            ? t("Local rehearsal", "本地演练")
            : job.request.start_url}{" "}
          · {t("Public browsing and preparation", "公开浏览与准备")}
        </p>
      )}
      {computer && job.state === "review" && (
        <small>
          {t(
            "Page screenshots are processed in the cloud. Final submissions need you.",
            "网页截图会交给云端助手处理，最终提交由你操作。",
          )}
        </small>
      )}
      {computer && job.result?.outcome === "needs_owner" && (
        <p>
          {job.result.readback?.reason === "provider_step_unavailable"
            ? t(
                "Alice could not complete this step. Check the connection before continuing.",
                "Alice 未能完成这一步，请检查连接后再继续。",
              )
            : job.request.start_url?.startsWith("demo:")
              ? t(
                  "Stopped before submission; no order or booking was made.",
                  "已停在提交前，没有下单或预订。",
                )
              : t(
                  "Complete account or submission steps on the website in your own browser.",
                  "账号或提交步骤需要在你自己的浏览器中完成。",
                )}
        </p>
      )}
      {isDesktopAction(job.action) && writing && (
        <p>
          {t(
            "Use Mousepad to save the text, then open it in Chromium to verify the result.",
            "使用 Mousepad 保存文字，再在 Chromium 中打开并核验结果。",
          )}
        </p>
      )}
      {application && step && <small>{step.filename}</small>}
      {job.state === "review" && (
        <details className="action-preview" open={!compact}>
          <summary>{t("Review content", "核对内容")}</summary>
          {application && step ? (
            <ApplicationPreview step={step} t={t} />
          ) : (
            <pre tabIndex={0}>{job.request.content}</pre>
          )}
          {computer && job.request.allowed_origins?.length ? (
            <small>
              {t("Allowed sites: ", "允许访问：")}
              {job.request.allowed_origins.join(", ")}
            </small>
          ) : null}
        </details>
      )}
      {job.state === "unknown" && (
        <p>
          {t(
            "Check the existing result before continuing.",
            "请先核验已有结果。",
          )}
        </p>
      )}
      {job.cancel_requested && job.state === "succeeded" && (
        <p>
          {computer
            ? t(
                "Earlier browser steps remain; cancellation does not undo them.",
                "先前的浏览器操作仍保留，取消不会撤销它们。",
              )
            : t(
                "The file had already been saved. Cancelling did not remove it.",
                "文件已经保存，取消没有删除它。",
              )}
        </p>
      )}
      {job.state === "expired" && (
        <p>
          {t(
            "This request expired before it ran. Ask Alice to prepare it again.",
            "请求已到期，尚未执行。可以让 Alice 重新准备。",
          )}
        </p>
      )}
      {!!job.error && !["expired", "cancelled"].includes(job.state) && (
        <p className="error-message">{errorText(new ApiError(job.error), t)}</p>
      )}
      {job.state !== "succeeded" && readBackCopy(job.result?.reason) && (
        <p>{t(...readBackCopy(job.result?.reason)!)}</p>
      )}

      <div className="workspace-inline-actions">
        {computer && job.result?.verified && onContinue && (
          <button
            type="button"
            className="secondary"
            disabled={!fresh || busy}
            onClick={onContinue}
          >
            {t("Continue from this page", "从这个页面继续")}
          </button>
        )}
        {job.state === "review" && (
          <button
            className="primary"
            disabled={
              busy ||
              !available ||
              (application && !step) ||
              !reviewAvailable(job, Date.now(), fresh)
            }
            onClick={() => onAction("approve")}
          >
            {t("Allow once", "允许这一次")}
          </button>
        )}
        {jobCancellable(job) && (
          <button
            className="secondary"
            disabled={cancelling}
            onClick={() => onAction("cancel")}
          >
            {job.state === "review"
              ? t("Not now", "暂不允许")
              : t("Stop action", "停止操作")}
          </button>
        )}
        {job.state === "unknown" && (
          <button
            className="primary"
            disabled={busy || !fresh || !available}
            onClick={() => onAction("reconcile")}
          >
            {t("Check result", "核验结果")}
          </button>
        )}
      </div>
      {computer &&
        (job.result?.verified ||
          ["running", "verifying", "succeeded", "unknown"].includes(
            job.state,
          )) && (
          <ComputerScreen
            key={job.id}
            jobId={job.id}
            refresh={refreshToken ?? Date.parse(job.updated_at)}
            t={t}
          />
        )}
      {application &&
        step &&
        job.state === "succeeded" &&
        job.result?.verified && (
          <div className="workspace-inline-actions">
            <ExportLink
              path={`/computer/jobs/${job.id}/artifact`}
              filename={step.filename}
              onError={setExportError}
            >
              {t("Download", "下载")}
            </ExportLink>
          </div>
        )}
      {!!exportError && (
        <p className="error-message" role="alert">
          {errorText(exportError, t)}
        </p>
      )}
      <details className="action-details">
        <summary>{t("Details", "详情")}</summary>
        {recoveryCopy(job) && <p>{t(...recoveryCopy(job)!)}</p>}
        {job.authorization && (
          <small className="action-authority">
            {job.authorization.mode === "full"
              ? t(
                  "Authorized by your full-access setting",
                  "已根据你的完整权限设置授权",
                )
              : t("Allowed once by you", "由你允许这一次")}
          </small>
        )}

        {job.state !== "review" && (
          <pre tabIndex={0}>{job.request.content}</pre>
        )}
        <p>
          {application && step
            ? step.filename
            : `${job.request.artifact_id}.${computer ? "json" : "txt"}`}
        </p>
        {job.result?.verified && (
          <>
            <p>
              {job.result.bytes} {t("bytes", "字节")}
            </p>
            <code>SHA256 {job.result.sha256}</code>
          </>
        )}
        {job.state === "review" && (
          <p>
            {t("Valid until ", "有效至 ")}
            {new Date(job.expires_at).toLocaleTimeString()}
          </p>
        )}
        {job.task_id && (
          <p>
            {t(
              "Linked to this task. The task's completion is recorded separately.",
              "已关联此事务；事务完成状态单独记录。",
            )}
          </p>
        )}
        {job.state === "succeeded" && writing && (
          <button
            className="text-button"
            disabled={busy || !fresh || !available}
            onClick={() => onAction("verify")}
          >
            {t("Check the file again", "再次核验文件")}
          </button>
        )}
      </details>
    </article>
  );
}
