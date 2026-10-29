import { DateTime } from "luxon";
import { FileCheck2 } from "lucide-react";
import type { Translate } from "../types";
import { jobStateLabel } from "./jobTypes";
import type { ComputerJobSummary } from "./jobTypes";

/** Uses safe task receipts; further actions continue in the shared assistant. */
export function TaskJobs({
  t,
  timezone,
  jobs,
  blocked,
  onDiscuss,
}: {
  t: Translate;
  timezone: string;
  jobs: ComputerJobSummary[] | undefined;
  blocked: boolean;
  onDiscuss: () => void;
}) {
  return (
    <section
      className="workspace-section task-job-results"
      aria-label={t("Task files and results", "事务文件与结果")}
    >
      <h3>{t("Files and results", "文件与结果")}</h3>
      <p className="workspace-hint">
        {t(
          "File verification does not complete this task. Review the result, then decide your next step.",
          "文件核验不会自动完成事务。请核对结果，再决定下一步。",
        )}
      </p>
      {!jobs && (
        <p role="status">{t("Loading linked results…", "正在读取关联结果…")}</p>
      )}
      {jobs?.length === 0 && (
        <p>{t("No file actions are linked yet.", "还没有关联的文件操作。")}</p>
      )}
      {jobs?.slice(0, 3).map((job) => (
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
          {job.state === "succeeded" && job.result?.verified ? (
            <p>
              <FileCheck2 size={16} /> {t("Result checked", "结果已核验")}
            </p>
          ) : job.state === "unknown" ? (
            <p>
              {t(
                "Check the existing result before preparing another write.",
                "请先核验已有结果，再决定是否准备另一次写入。",
              )}
            </p>
          ) : null}
          {job.result?.artifact && (
            <details>
              <summary>{t("File details", "文件详情")}</summary>
              <code>{job.result.artifact}</code>
            </details>
          )}
        </article>
      ))}
      {!!jobs && jobs.length > 3 && (
        <p className="workspace-hint">
          {t(
            `Showing 3 of ${jobs.length} linked actions.`,
            `显示 ${jobs.length} 项关联操作中的 3 项。`,
          )}
        </p>
      )}
      <button className="secondary" disabled={blocked} onClick={onDiscuss}>
        {t("Continue with Alice", "和 Alice 继续处理")}
      </button>
    </section>
  );
}
