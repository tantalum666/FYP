import { useCallback, useEffect, useRef, useState } from "react";
import { FileCheck2, FolderPen } from "lucide-react";
import {
  ApiError,
  errorText,
  pendingWrite,
  request,
  retryPending,
  write,
} from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import {
  jobCancellable,
  recoveryMatchesNote,
  reviewAvailable,
} from "./jobTypes";
import type { ComputerJob, JobState } from "./jobTypes";
import type { Task } from "./taskTypes";

interface Snapshot {
  enabled: boolean;
  jobs: ComputerJob[];
}

export function ComputerJobsPanel({
  t,
  taskId,
}: {
  t: Translate;
  taskId?: string;
}) {
  const { data, offline, stale } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [lastRead, setLastRead] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const alive = useRef(false);
  const generation = useRef(0);
  const reading = useRef<number | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const cancelGuard = useRef(false);
  const fresh =
    !readError && !offline && !stale && Date.now() - lastRead < 6000;
  useDraftGuard(!!(title.trim() || content.trim()), busy);
  const reload = useCallback(async () => {
    const started = generation.current;
    if (!owner || reading.current === started) return;
    reading.current = started;
    try {
      const next = await request<Snapshot>(
        `/computer/jobs${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ""}`,
      );
      if (alive.current && generation.current === started) {
        setSnapshot(next);
        setReadError(null);
        setLastRead(Date.now());
      }
    } catch (e) {
      if (alive.current && generation.current === started) setReadError(e);
    } finally {
      if (reading.current === started) reading.current = null;
    }
  }, [owner, taskId]);
  useEffect(() => {
    generation.current += 1;
    alive.current = true;
    setSnapshot(null);
    setLastRead(0);
    void reload();
    const timer = setInterval(() => {
      if (!document.hidden) void reload();
    }, 2000);
    window.addEventListener("desk:jobs", reload);
    document.addEventListener("visibilitychange", reload);
    return () => {
      alive.current = false;
      generation.current += 1;
      clearInterval(timer);
      window.removeEventListener("desk:jobs", reload);
      document.removeEventListener("visibilitychange", reload);
    };
  }, [reload]);
  async function prepare(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const task = taskId
        ? (await request<{ task: Task }>(`/tasks/${taskId}`)).task
        : null;
      await write("/computer/jobs", {
        action: "save_note",
        title,
        content,
        task_id: taskId ?? null,
        task_version: task?.version ?? null,
      });
      setTitle("");
      setContent("");
      setExpanded(false);
      setNotice(
        t(
          "Prepared for review. No file has been written.",
          "已准备待核对，尚未写入文件。",
        ),
      );
      await reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function cancel(job: ComputerJob) {
    // Cancellation must remain reachable while an approval's HTTP result is
    // unknown. It does not share the normal write queue or its busy flag.
    if (cancelGuard.current) return;
    cancelGuard.current = true;
    setCancelling(true);
    setError(null);
    try {
      await request(`/computer/jobs/${job.id}/cancel`, {
        method: "POST",
        body: "{}",
        headers: { "X-Operation-Id": `computer-cancel/${job.id}` },
      });
      setNotice(
        t(
          "Cancellation requested. Check the current result; an existing file is not rolled back.",
          "已请求取消。请核对当前结果，已写入的文件不会回滚。",
        ),
      );
      await reload();
    } catch (e) {
      setError(e);
    } finally {
      cancelGuard.current = false;
      setCancelling(false);
    }
  }
  async function action(
    job: ComputerJob,
    kind: "approve" | "reconcile" | "verify",
  ) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      if (kind === "approve") {
        await write(`/computer/jobs/${job.id}/approve`, {
          expected_version: job.version,
          intent_hash: job.intent_hash,
        });
      } else if (kind === "verify") {
        const task = taskId
          ? (await request<{ task: Task }>(`/tasks/${taskId}`)).task
          : null;
        await write("/computer/jobs", {
          action: "verify_note",
          title: t("Verify saved note", "核验已保存笔记"),
          source_job_id: job.id,
          task_id: taskId ?? null,
          task_version: task?.version ?? null,
        });
      } else {
        // Read-only reconciliation does not replay an uncertain write.
        await request(`/computer/jobs/${job.id}/${kind}`, {
          method: "POST",
          body: "{}",
          headers: { "X-Operation-Id": `computer-reconcile/${job.id}` },
        });
      }
      setNotice(
        kind === "verify"
          ? t("Verification prepared for review.", "核验作业已准备待核对。")
          : kind === "approve"
            ? t(
                "Approval request processed. Check the current status below; the desk keeps the job and its result.",
                "批准请求已处理，请核对下方当前状态。桌面服务会保留作业和结果。",
              )
            : t(
                "Read-back check finished. Review the result below.",
                "读回检查已结束，请查看下方结果。",
              ),
      );
      await reload();
    } catch (e) {
      setError(e);
      await reload();
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<JobState, string> = {
    review: t("Needs your approval", "待你批准"),
    queued: t("Queued", "已排队"),
    running: t("Saving or checking", "正在保存或检查"),
    verifying: t("Verifying result", "正在核验结果"),
    succeeded: t("Verified", "已核验"),
    failed: t("Could not execute", "未能执行"),
    cancel_requested: t("Stopping · result pending", "正在停止 · 结果待确认"),
    cancelled: t("Cancelled before execution", "已在执行前取消"),
    expired: t("Expired without execution", "已到期，未执行"),
    unknown: t("Result unknown · check before retrying", "结果未知 · 请先核验"),
  };
  if (!owner)
    return (
      <section className="workspace-section">
        <h3>{t("Computer jobs", "电脑作业")}</h3>
        <p>
          {t(
            "Sign in as owner to review and approve computer jobs. Pairing alone does not grant execution permission.",
            "请以拥有者身份登录，核对并批准电脑作业。配对身份不会自动获得执行权限。",
          )}
        </p>
      </section>
    );
  return (
    <section
      className="workspace-section computer-jobs"
      aria-label={t("Computer jobs", "电脑作业")}
    >
      <div className="workspace-state">
        <FolderPen />
        <div>
          <h3>{t("Computer jobs", "电脑作业")}</h3>
          <p>
            {t(
              "Save a note in this desk’s dedicated notes folder, then verify the actual file. Each job needs your approval.",
              "将笔记保存到本桌面的专用笔记目录，再核验实际文件。每项作业都需要你批准。",
            )}
          </p>
        </div>
      </div>
      {snapshot && !snapshot.enabled && (
        <p role="status">
          {t(
            "Local note execution is disabled on this desk. The operator can enable the bounded notes adapter using the setup guide.",
            "本桌面尚未启用本地笔记执行，操作人员可按安装说明启用受限笔记适配器。",
          )}
        </p>
      )}
      {!!readError && (
        <p role="alert" className="error-message">
          {t(
            "Job status is unavailable. Approval is paused until the connection returns.",
            "暂时无法读取作业状态，恢复连接后才可批准。",
          )}
        </p>
      )}
      {snapshot?.enabled && (
        <>
          <button
            type="button"
            className="secondary"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {t("Prepare a note", "准备笔记")}
          </button>
          {expanded && (
            <form onSubmit={prepare}>
              <label className="field">
                {t("Note title", "笔记标题")}
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={120}
                  required
                  disabled={busy}
                />
              </label>
              <label className="field">
                {t("Exact note text", "笔记全文")}
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  maxLength={8000}
                  rows={4}
                  required
                  disabled={busy}
                />
              </label>
              <button
                className="primary"
                disabled={busy || !fresh || !title.trim() || !content.trim()}
              >
                {t("Prepare for review", "准备待核对")}
              </button>
            </form>
          )}
        </>
      )}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      {pendingWrite()?.path.startsWith("/computer/") && (
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              const recovered = pendingWrite();
              await retryPending();
              if (recoveryMatchesNote(recovered, title, content, taskId)) {
                setTitle("");
                setContent("");
              }
              await reload();
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("Recover pending request", "恢复待确认请求")}
        </button>
      )}
      {snapshot?.jobs.length === 0 && (
        <p className="workspace-hint">
          {t(
            "No computer jobs yet. Prepared and completed jobs remain here after you return.",
            "尚无电脑作业。离开后返回，仍可在此查看待批准作业和已完成结果。",
          )}
        </p>
      )}
      {snapshot?.jobs.map((job) => (
        <article key={job.id} className="computer-job">
          <div className="workspace-eyebrow">{labels[job.state]}</div>
          <h4>{job.request.title}</h4>
          <p>
            {job.action === "save_note"
              ? t("Save a new note", "保存新笔记")
              : t("Verify an existing note", "核验已有笔记")}
          </p>
          <p className="job-target">
            {t(
              "Destination: Desk Companion notes / ",
              "目标：Desk Companion 笔记目录 / ",
            )}
            {job.request.artifact_id}.txt
          </p>
          <details open={job.state === "review"}>
            <summary>{t("Review exact text", "核对笔记全文")}</summary>
            <pre tabIndex={0}>{job.request.content}</pre>
          </details>
          {job.task_id && (
            <small>
              {t(
                "Linked to the same task; this does not mark it complete.",
                "关联原事务，不会自动将事务标为完成。",
              )}
            </small>
          )}
          {job.state === "review" && (
            <p>
              {t("Approval expires at ", "批准有效至 ")}
              {new Date(job.expires_at).toLocaleTimeString()}
            </p>
          )}
          {job.result?.verified && (
            <p className="job-receipt">
              <FileCheck2 size={18} />
              {t("Independent read-back matched", "独立读回一致")} ·{" "}
              {job.result.bytes} {t("bytes", "字节")}
              <code>SHA256 {job.result.sha256}</code>
            </p>
          )}
          {job.cancel_requested && job.state === "succeeded" && (
            <p>
              {t(
                "The file was already committed and verified. Cancellation did not remove it.",
                "文件已写入并核验，取消没有删除已产生的结果。",
              )}
            </p>
          )}
          {job.state === "unknown" && (
            <p>
              {t(
                "Execution will not be repeated automatically. Check the existing file result first.",
                "不会自动重复执行。请先核验已有文件结果。",
              )}
            </p>
          )}
          {job.error && (
            <p className="workspace-hint">
              {errorText(new ApiError(job.error), t)}
            </p>
          )}
          <div className="workspace-inline-actions">
            {job.state === "review" && (
              <button
                className="primary"
                disabled={
                  busy ||
                  !snapshot.enabled ||
                  !reviewAvailable(job, Date.now(), fresh)
                }
                onClick={() => void action(job, "approve")}
              >
                {t("Approve this job", "批准此作业")}
              </button>
            )}
            {jobCancellable(job) && (
              <button
                className="secondary"
                disabled={cancelling || offline}
                onClick={() => void cancel(job)}
              >
                {t("Cancel job", "取消作业")}
              </button>
            )}
            {job.state === "unknown" && (
              <button
                className="secondary"
                disabled={busy || !fresh || !snapshot.enabled}
                onClick={() => void action(job, "reconcile")}
              >
                {t("Check existing result", "核验已有结果")}
              </button>
            )}
            {job.state === "succeeded" && job.action === "save_note" && (
              <button
                className="text-button"
                disabled={busy || !fresh || !snapshot.enabled}
                onClick={() => void action(job, "verify")}
              >
                {t("Prepare another verification", "准备再次核验")}
              </button>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
