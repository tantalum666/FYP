import { useEffect, useRef, useState } from "react";
import type { Translate } from "../types";
import { request, errorText } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { MutationFeedback } from "./personal/MutationFeedback";
import type { Task } from "./taskTypes";
import type { ComputerJob } from "./jobTypes";
import { useWorkspace } from "./WorkspaceContext";
import "./computer-use.css";

export function ComputerUseComposer({
  t,
  available,
  taskId,
  initialGoal = "",
  onPrepared,
  resumeJob,
  onNew,
  initiallyOpen = false,
}: {
  t: Translate;
  available: boolean;
  taskId?: string;
  initialGoal?: string;
  onPrepared: () => void;
  resumeJob?: ComputerJob;
  onNew?: () => void;
  initiallyOpen?: boolean;
}) {
  const [goal, setGoal] = useState(initialGoal);
  const { data } = useWorkspace();
  const full = data?.permissions?.mode === "full";
  const [site, setSite] = useState(resumeJob?.request.start_url ?? "");
  const [kind, setKind] = useState(
    resumeJob?.request.start_url?.startsWith("demo:")
      ? resumeJob.request.start_url
      : "website",
  );
  const [shared, setShared] = useState(false);
  const [extraSites, setExtraSites] = useState(
    resumeJob?.request.allowed_origins?.join(" ") ?? "",
  );
  const mutation = usePrivateMutation();
  const section = useRef<HTMLDetailsElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const locked = mutation.busy || mutation.pending;
  const [error, setError] = useState<unknown>(null);
  useDraftGuard(!!goal.trim() || mutation.pending, mutation.busy);
  useEffect(() => {
    if (initialGoal || resumeJob) input.current?.focus({ preventScroll: true });
    if (resumeJob) section.current?.scrollIntoView({ block: "start" });
  }, [initialGoal, resumeJob?.id]);
  async function prepare(event: React.FormEvent) {
    event.preventDefault();
    if (!available || !shared || mutation.busy || mutation.pending) return;
    setError(null);
    try {
      const selectedTask = resumeJob?.task_id ?? taskId;
      const task = selectedTask
        ? (await request<{ task: Task }>(`/tasks/${selectedTask}`)).task
        : null;
      await mutation.run(
        "/computer/computer-use/jobs",
        {
          action: "computer_use",
          title: Array.from(goal.trim()).slice(0, 120).join(""),
          goal: goal.trim(),
          start_url: kind === "website" ? site.trim() : kind,
          allowed_origins:
            kind === "website" ? extraSites.split(/\s+/).filter(Boolean) : [],
          public_only: true,
          share_screen: true,
          max_steps: 8,
          task_id: selectedTask ?? null,
          task_version: task?.version ?? null,
          source_job_id: resumeJob?.id ?? null,
        },
        () => {
          setGoal("");
          setShared(false);
          onPrepared();
        },
      );
    } catch (failure) {
      setError(failure);
    }
  }
  return (
    <details
      ref={section}
      className="computer-use-composer"
      open={initialGoal || resumeJob || initiallyOpen ? true : undefined}
    >
      <summary>{t("Browse the web", "浏览网页")}</summary>
      {resumeJob && (
        <p>
          {t(
            "Continue the saved public-page state.",
            "继续之前保存的公开网页状态。",
          )}{" "}
          <button className="text-button" type="button" onClick={onNew}>
            {t("Start fresh", "重新开始")}
          </button>
        </p>
      )}
      <form onSubmit={(event) => void prepare(event)}>
        <label>
          {t("What would you like to do?", "想让 Alice 做什么？")}
          <textarea
            ref={input}
            disabled={locked}
            value={goal}
            maxLength={2000}
            required
            onChange={(event) => setGoal(event.target.value)}
          />
        </label>
        <details className="computer-use-options">
          <summary>{t("More options", "更多选项")}</summary>
          <label>
            {t("Where", "在哪里操作")}
            <select
              value={kind}
              disabled={locked || !!resumeJob}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="website">{t("Public website", "公开网站")}</option>
              <option value="demo:shopping">
                {t("Shopping rehearsal", "购物演练")}
              </option>
              <option value="demo:flights">
                {t("Flight rehearsal", "机票演练")}
              </option>
            </select>
          </label>
        </details>
        {kind === "website" && (
          <label>
            {t("Website", "网站地址")}
            <input
              type="url"
              placeholder="https://…"
              value={site}
              disabled={locked || !!resumeJob}
              required
              onChange={(event) => setSite(event.target.value)}
            />
          </label>
        )}
        <p className="workspace-hint">
          {t(
            "Prepare and compare. Sign-in, personal details and final submissions need you.",
            "可以查找、比较和准备；登录、个人资料及最终提交由你处理。",
          )}
        </p>
        <label className="computer-use-consent">
          <input
            type="checkbox"
            checked={shared}
            disabled={locked}
            onChange={(event) => setShared(event.target.checked)}
          />
          {t(
            "Allow Alice to use this task and page screenshots in the cloud",
            "允许 Alice 在云端处理本次任务和网页截图",
          )}
        </label>
        <small>
          {t(
            "Uses your assistant allowance. You can stop at any time.",
            "会使用助理额度，你可以随时停止。",
          )}
        </small>
        {kind === "website" && (
          <details>
            <summary>{t("Additional sites", "其他允许访问的网站")}</summary>
            <input
              aria-label={t("Additional site origins", "其他网站来源")}
              placeholder="https://example.com"
              value={extraSites}
              disabled={locked || !!resumeJob}
              onChange={(event) => setExtraSites(event.target.value)}
            />
          </details>
        )}
        {!available && (
          <p role="status">
            {t(
              "Browser operation is unavailable on this desk.",
              "当前桌面的浏览器操作暂不可用。",
            )}
          </p>
        )}
        <button
          className="primary"
          disabled={
            !available ||
            !shared ||
            !goal.trim() ||
            mutation.busy ||
            mutation.pending
          }
        >
          {full
            ? t("Start browser task", "开始浏览器任务")
            : t("Prepare for review", "准备并核对")}
        </button>
      </form>
      <MutationFeedback mutation={mutation} t={t} />
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </details>
  );
}
