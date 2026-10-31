import { Check, FileText, LoaderCircle } from "lucide-react";
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

export function JobActionCard({
  job,
  t,
  busy,
  cancelling,
  fresh,
  available,
  onAction,
  compact = false,
}: {
  job: ComputerJob;
  t: Translate;
  busy: boolean;
  cancelling: boolean;
  fresh: boolean;
  available: boolean;
  onAction: (action: JobAction) => void;
  compact?: boolean;
}) {
  const [exportError, setExportError] = useState<unknown>(null);
  const application = isApplicationAction(job.action);
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
        {job.state === "succeeded" ? (
          <Check size={18} />
        ) : waiting ? (
          <LoaderCircle size={18} />
        ) : (
          <FileText size={18} />
        )}
        <div>
          <span className="action-state">
            {job.state === "review"
              ? t("Permission needed", "需要你的允许")
              : jobStateLabel(job.state, t)}
          </span>
          <h4>{job.request.title}</h4>
        </div>
      </header>
      {!application && (
        <p>
          {writing
            ? t("Save a new file in ", "在以下位置保存新文件：")
            : t("Check the saved file in ", "核验以下位置的已有文件：")}
          {destination}.
        </p>
      )}
      {application && (
        <p>
          {t(
            "Use the connected applications in this task's workspace.",
            "在本事务的工作空间使用已连接的应用。",
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
        </details>
      )}
      {job.state === "succeeded" && job.result?.verified && (
        <p className="action-outcome">
          {writing
            ? t("Saved and independently verified.", "已保存，并通过独立核验。")
            : t(
                "The existing file still matches the approved content.",
                "已有文件仍与批准的内容一致。",
              )}
        </p>
      )}
      {job.state === "unknown" && (
        <p>
          {t(
            "The result needs checking. I will not repeat the write.",
            "结果需要核验，不会重复写入。",
          )}
        </p>
      )}
      {job.cancel_requested && job.state === "succeeded" && (
        <p>
          {t(
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
      {readBackCopy(job.result?.reason) && (
        <p>{t(...readBackCopy(job.result?.reason)!)}</p>
      )}
      {recoveryCopy(job) && <p>{t(...recoveryCopy(job)!)}</p>}
      <div className="workspace-inline-actions">
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
              {t("Download verified file", "下载已核验文件")}
            </ExportLink>
          </div>
        )}
      {!!exportError && (
        <p className="error-message" role="alert">
          {errorText(exportError, t)}
        </p>
      )}
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
      <details className="action-details">
        <summary>{t("Details", "详情")}</summary>
        {job.state !== "review" && (
          <pre tabIndex={0}>{job.request.content}</pre>
        )}
        <p>
          {application && step
            ? step.filename
            : `${job.request.artifact_id}.txt`}
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
