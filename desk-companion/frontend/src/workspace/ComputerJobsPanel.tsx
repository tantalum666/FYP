import { useCallback, useEffect, useRef, useState } from "react";
import { FolderPen } from "lucide-react";
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
  isFolderAction,
  isDesktopAction,
  isApplicationAction,
  recoveryMatchesNote,
} from "./jobTypes";
import { JobActionCard } from "./JobActionCard";
import { requestJobAction } from "./jobRequests";
import type { JobAction } from "./jobRequests";
import type { ComputerJob } from "./jobTypes";
import type { Task } from "./taskTypes";
import { ComputerUseComposer } from "./ComputerUseComposer";

interface Snapshot {
  enabled: boolean;
  desktop?: { enabled: boolean; ready: boolean; apps: string[] };
  applications?: { enabled: boolean; configured: boolean };
  computer_use?: { enabled: boolean; configured: boolean };
  folder?: { configured: boolean; label: string | null };
  jobs: ComputerJob[];
}

export function ComputerJobsPanel({
  t,
  taskId,
  computerGoal,
  onComputerPrepared,
  active = true,
}: {
  t: Translate;
  taskId?: string;
  computerGoal?: { text: string; key: number };
  onComputerPrepared?: () => void;
  active?: boolean;
}) {
  const { data, offline, stale } = useWorkspace();
  const owner =
    data?.principal.kind === "owner" && data.personal_context_visible;
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [folderLabel, setFolderLabel] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [folderTitle, setFolderTitle] = useState("");
  const [folderContent, setFolderContent] = useState("");
  const [folderExpanded, setFolderExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [lastRead, setLastRead] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [resumeBrowser, setResumeBrowser] = useState<ComputerJob>();
  const [noteAction, setNoteAction] = useState<
    "save_note" | "linux_note_preview"
  >("save_note");
  const effectiveAction =
    !snapshot?.enabled && snapshot?.desktop?.ready
      ? "linux_note_preview"
      : noteAction;
  const executorAvailable = (job: ComputerJob) =>
    job.action === "computer_use"
      ? ["unknown", "succeeded"].includes(job.state) ||
        (snapshot?.computer_use?.enabled && snapshot.computer_use.configured)
      : isApplicationAction(job.action)
        ? snapshot?.applications?.enabled && snapshot.applications.configured
        : isDesktopAction(job.action)
          ? snapshot?.desktop?.ready
          : isFolderAction(job.action)
            ? snapshot?.folder?.configured
            : snapshot?.enabled;
  const alive = useRef(false);
  const generation = useRef(0);
  const reading = useRef<number | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const cancelGuard = useRef(false);
  const fresh =
    !readError && !offline && !stale && Date.now() - lastRead < 6000;
  useDraftGuard(
    !!(
      title.trim() ||
      content.trim() ||
      folderLabel.trim() ||
      folderPath.trim() ||
      folderTitle.trim() ||
      folderContent.trim()
    ),
    busy,
  );
  const reload = useCallback(async () => {
    const started = generation.current;
    if (!active || !owner || reading.current === started) return;
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
  }, [active, owner, taskId]);
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
        action: effectiveAction,
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
  async function nameFolder(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write("/computer/folder", { label: folderLabel, path: folderPath });
      setFolderLabel("");
      setFolderPath("");
      setNotice(
        t(
          "Folder saved. New folder jobs use this directory only after you approve the full text.",
          "文件夹已保存。新的文件夹作业仍需你批准全文后才会写入。",
        ),
      );
      await reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function clearFolder() {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write("/computer/folder/clearance", {});
      setNotice(
        t(
          "Folder cleared. Existing files stay where they are. Jobs that already named this folder cannot run.",
          "已清除文件夹指定。已有文件仍留在原处。已经绑定该文件夹的作业不能再执行。",
        ),
      );
      await reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function prepareFolder(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const task = taskId
        ? (await request<{ task: Task }>(`/tasks/${taskId}`)).task
        : null;
      await write("/computer/jobs", {
        action: "save_folder_file",
        title: folderTitle,
        content: folderContent,
        task_id: taskId ?? null,
        task_version: task?.version ?? null,
      });
      setFolderTitle("");
      setFolderContent("");
      setFolderExpanded(false);
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
      await requestJobAction(job, "cancel");
      setNotice(
        job.action === "computer_use"
          ? t(
              "Stop requested; earlier browser steps may remain.",
              "已请求停止，先前的浏览器操作可能已生效。",
            )
          : t(
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
  async function action(job: ComputerJob, kind: Exclude<JobAction, "cancel">) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await requestJobAction(job, kind);
      setNotice(
        job.action === "computer_use"
          ? ""
          : kind === "verify"
            ? isApplicationAction(job.action)
              ? t(
                  "The current file matches the verified operation.",
                  "当前文件与已核验操作一致。",
                )
              : t("Verification prepared for review.", "核验作业已准备待核对。")
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

  if (!owner)
    return (
      <section className="workspace-section">
        <h3>{t("File activity", "文件活动")}</h3>
        <p>
          {data?.principal.kind === "owner"
            ? t(
                "Private view is hidden. Reveal it to review computer tasks.",
                "当前已隐藏私人内容，显示后可查看电脑任务。",
              )
            : t(
                "Review and approve computer jobs from your main desk.",
                "请在主桌面核对并批准电脑作业。",
              )}
        </p>
      </section>
    );
  return (
    <section
      className="workspace-section computer-jobs"
      aria-label={t("File activity", "文件活动")}
    >
      <div className="workspace-state">
        <FolderPen />
        <div>
          <h3>{t("Computer activity", "电脑操作")}</h3>
          <p>
            {t("Review browser and file actions.", "核对浏览器和文件操作。")}
          </p>
        </div>
      </div>
      <ComputerUseComposer
        key={resumeBrowser?.id ?? computerGoal?.key ?? 0}
        initialGoal={computerGoal?.text}
        initiallyOpen={!!computerGoal}
        t={t}
        taskId={taskId}
        resumeJob={resumeBrowser}
        onNew={() => setResumeBrowser(undefined)}
        available={
          !!snapshot?.computer_use?.enabled &&
          snapshot.computer_use.configured &&
          fresh
        }
        onPrepared={() => {
          setResumeBrowser(undefined);
          onComputerPrepared?.();
          void reload();
        }}
      />
      {snapshot &&
        !snapshot.enabled &&
        !snapshot.computer_use?.enabled &&
        !snapshot.applications?.enabled && (
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
      <details className="job-folder-settings">
        <summary>{t("Folder settings", "文件夹设置")}</summary>
        <form onSubmit={nameFolder}>
          <p className="workspace-hint">
            {snapshot?.folder?.configured
              ? t("Current folder: ", "当前文件夹：") +
                (snapshot.folder.label ?? "")
              : t(
                  "No folder is named yet. Folder jobs stay unavailable until you choose one existing directory outside this desk’s runtime data.",
                  "尚未指定文件夹。在你选择本桌面运行数据之外的一个已有目录之前，文件夹作业不可用。",
                )}
          </p>
          <label className="field">
            {t("Folder label", "文件夹名称")}
            <input
              value={folderLabel}
              onChange={(e) => setFolderLabel(e.target.value)}
              maxLength={80}
              required
              disabled={busy}
            />
          </label>
          <label className="field">
            {t("Absolute folder path", "文件夹绝对路径")}
            <input
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              maxLength={4096}
              required
              disabled={busy}
              spellCheck={false}
              autoComplete="off"
            />
          </label>
          <div className="workspace-inline-actions">
            <button
              className="primary"
              disabled={
                busy || !fresh || !folderLabel.trim() || !folderPath.trim()
              }
            >
              {t("Save this folder", "保存此文件夹")}
            </button>
            {snapshot?.folder?.configured && (
              <button
                type="button"
                className="secondary"
                disabled={busy || !fresh}
                onClick={() => void clearFolder()}
              >
                {t("Clear folder", "清除文件夹")}
              </button>
            )}
          </div>
        </form>
      </details>
      {snapshot?.folder?.configured && (
        <>
          <button
            type="button"
            className="secondary"
            onClick={() => setFolderExpanded(!folderExpanded)}
            aria-expanded={folderExpanded}
          >
            {t("Prepare a folder file", "准备文件夹文件")}
          </button>
          {folderExpanded && (
            <form onSubmit={prepareFolder}>
              <label className="field">
                {t("File title", "文件标题")}
                <input
                  value={folderTitle}
                  onChange={(e) => setFolderTitle(e.target.value)}
                  maxLength={120}
                  required
                  disabled={busy}
                />
              </label>
              <label className="field">
                {t("Exact file text", "文件全文")}
                <textarea
                  value={folderContent}
                  onChange={(e) => setFolderContent(e.target.value)}
                  maxLength={8000}
                  rows={4}
                  required
                  disabled={busy}
                />
              </label>
              <button
                className="primary"
                disabled={
                  busy || !fresh || !folderTitle.trim() || !folderContent.trim()
                }
              >
                {t("Prepare for review", "准备待核对")}
              </button>
            </form>
          )}
        </>
      )}
      {(snapshot?.enabled || snapshot?.desktop?.ready) && (
        <>
          <button
            type="button"
            className="secondary"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {t("Prepare a note or app workflow", "准备笔记或跨应用操作")}
          </button>
          {expanded && (
            <form onSubmit={prepare}>
              <label className="field">
                {t("How to save", "保存方式")}
                <select
                  value={effectiveAction}
                  onChange={(e) =>
                    setNoteAction(
                      e.target.value as "save_note" | "linux_note_preview",
                    )
                  }
                  disabled={busy}
                >
                  {snapshot?.enabled && (
                    <option value="save_note">
                      {t("Save in notes folder", "保存到笔记目录")}
                    </option>
                  )}
                  {snapshot?.desktop?.ready && (
                    <option value="linux_note_preview">
                      {t(
                        "Mousepad → Chromium preview",
                        "Mousepad 编辑 → Chromium 预览",
                      )}
                    </option>
                  )}
                </select>
              </label>
              {effectiveAction === "linux_note_preview" && (
                <p>
                  {t(
                    "Opens separate editor and browser windows on this Linux desktop, then verifies the saved text. Existing documents stay untouched.",
                    "在本台 Linux 桌面打开独立的编辑器和浏览器窗口，然后核对保存的全文。已有文档保持不变。",
                  )}
                </p>
              )}
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
              if (
                recoveryMatchesNote(
                  recovered,
                  title,
                  content,
                  taskId,
                  effectiveAction,
                )
              ) {
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
        <JobActionCard
          key={job.id}
          job={job}
          t={t}
          busy={busy}
          cancelling={cancelling || offline}
          fresh={fresh}
          available={!!executorAvailable(job)}
          refreshToken={lastRead}
          onContinue={
            job.action === "computer_use"
              ? () => setResumeBrowser(job)
              : undefined
          }
          onAction={(kind) =>
            void (kind === "cancel" ? cancel(job) : action(job, kind))
          }
        />
      ))}
    </section>
  );
}
