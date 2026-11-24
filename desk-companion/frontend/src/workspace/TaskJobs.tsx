import { DateTime } from "luxon";
import { FileCheck2 } from "lucide-react";
import { useState } from "react";
import { ApiError, errorText } from "../api";
import type { Translate } from "../types";
import { jobStateLabel, taskRecoveryGuidance } from "./jobTypes";
import type { ComputerJobSummary } from "./jobTypes";
import type { ApplicationState } from "./applicationTypes";
import { ExportLink } from "./ExportLink";

/** Uses safe task receipts; further actions continue in the shared assistant. */
export function TaskJobs({
  t,
  timezone,
  jobs,
  blocked,
  onDiscuss,
  application,
}: {
  t: Translate;
  timezone: string;
  jobs: ComputerJobSummary[] | undefined;
  blocked: boolean;
  onDiscuss: () => void;
  application?: ApplicationState | null;
}) {
  const [exportError, setExportError] = useState<unknown>(null);
  const notes = jobs?.filter((job) => job.action !== "application");
  const hold = notes?.some((job) => {
    const kind = taskRecoveryGuidance(job)?.kind;
    return kind === "unknown" || kind === "needs_approval";
  });
  return (
    <section
      className="workspace-section task-job-results"
      aria-label={t("Task files and results", "事务文件与结果")}
    >
      <h3>{t("Files and results", "文件与结果")}</h3>
      {!!application?.stages.length && (
        <div
          className="application-stages"
          aria-label={t("Application progress", "应用操作进度")}
        >
          {application.stages.map((stage) => (
            <article key={stage.stage} className="task-job-result">
              <strong>{stage.title}</strong>
              <small>
                {jobStateLabel(stage.state, t)} · {stage.filename}
              </small>
              {stage.error &&
                !["cancelled", "expired"].includes(stage.state) && (
                  <p>{errorText(new ApiError(stage.error), t)}</p>
                )}
            </article>
          ))}
        </div>
      )}
      {!!application?.artifacts.length && (
        <div
          className="workspace-inline-actions"
          aria-label={t("Last verified files", "最近核验通过的文件")}
        >
          {application.artifacts.map((artifact) => (
            <ExportLink
              key={artifact.job_id}
              path={`/computer/jobs/${artifact.job_id}/artifact`}
              filename={artifact.filename}
              onError={setExportError}
            >
              {artifact.filename}
            </ExportLink>
          ))}
        </div>
      )}
      {!!exportError && (
        <p className="error-message" role="alert">
          {errorText(exportError, t)}
        </p>
      )}
      {!jobs && (
        <p role="status">{t("Loading linked results…", "正在读取关联结果…")}</p>
      )}
      {jobs?.length === 0 && (
        <p>{t("No file actions are linked yet.", "还没有关联的文件操作。")}</p>
      )}
      {notes?.slice(0, 3).map((job) => {
        const guidance = taskRecoveryGuidance(job);
        return (
        <article key={job.id} className="task-job-result">
          <strong>{job.title ?? t("File action", "文件操作")}</strong>
          <small>
            {jobStateLabel(job.state, t)} ·{" "}
            <time dateTime={job.updated_at}>
              {DateTime.fromISO(job.updated_at)
                .setZone(timezone)
                .setLocale(t("en-GB", "zh-CN"))
                .toFormat("d LLL HH:mm")}
            </time>
          </small>
          {guidance && (
            <p className={`task-recovery task-recovery-${guidance.kind}`}>
              {guidance.kind === "checked" && <FileCheck2 size={16} />}
              {t(...guidance.text)}
            </p>
          )}
          {job.result?.artifact && (
            <details>
              <summary>{t("File details", "文件详情")}</summary>
              <code>{job.result.artifact}</code>
            </details>
          )}
        </article>
        );
      })}
      {!!notes && notes.length > 3 && (
        <p className="workspace-hint">
          {t(
            `Showing 3 of ${notes.length} linked file actions.`,
            `显示 ${notes.length} 项关联文件操作中的 3 项。`,
          )}
        </p>
      )}
      {hold && (
        <p className="workspace-hint task-recovery-hold">
          {t(
            "Discussing this task does not check, approve, or write the file again.",
            "讨论这个事务不会核验、批准或再次写入文件。",
          )}
        </p>
      )}
      <button className="secondary" disabled={blocked} onClick={onDiscuss}>
        {hold
          ? t("Discuss this task", "讨论这个事务")
          : t("Continue with Alice", "和 Alice 继续处理")}
      </button>
    </section>
  );
}
