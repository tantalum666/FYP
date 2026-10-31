import { RunApplicationJobs } from "./RunApplicationJobs";
import { VoiceOriginLabel } from "../voiceWork/VoiceWorkPanel";
import { useState } from "react";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import { ArtifactList } from "./ArtifactList";
import { RunBrowserJobs } from "./RunBrowserJobs";
import { RunConnectorResults } from "./RunConnectorResults";
import { blockLabel, modeLabel, stateLabel } from "./labels";
import { RequestFeedback } from "./RequestFeedback";
import { canReviewProposal, runActions } from "./types";
import type { RunAction, RunDetailResponse } from "./types";
function actionLabel(action: RunAction, t: Translate) {
  return {
    pause: t("Pause", "暂停"),
    resume: t("Review and resume", "审阅并恢复"),
    cancel: t("Cancel work", "取消工作"),
    steer: t("Change the goal", "调整目标"),
    answer: t("Answer question", "回答问题"),
    retry_model: t("Review a new model attempt", "审阅新的模型尝试"),
  }[action];
}
export function RunDetail({
  detail,
  t,
  fence,
  fresh,
  onChanged,
  onReviewProposal,
  onReviewBrowserJob,
  onReviewConnectorIntent,
}: {
  detail: RunDetailResponse;
  t: Translate;
  fence: ResponseFence;
  fresh: boolean;
  onChanged: () => void;
  onReviewProposal?: (id: string) => void;
  onReviewBrowserJob?: (id: string) => void;
  onReviewConnectorIntent?: (id: string) => void;
}) {
  const run = detail.run;
  const mutation = usePrivateMutation(),
    cancellation = usePrivateMutation();
  const [editor, setEditor] = useState<{
    action: Exclude<RunAction, "cancel">;
    version: number;
    text: string;
    question?: string | null;
  } | null>(null);
  const [cancelVersion, setCancelVersion] = useState<number | null>(null);
  const locked = mutation.busy || mutation.pending;
  const cancelLocked = cancellation.busy || cancellation.pending;
  useDraftGuard(
    !!editor ||
      cancelVersion !== null ||
      mutation.pending ||
      cancellation.pending,
    mutation.busy || cancellation.busy,
  );
  async function perform(action: RunAction, version: number, text = "") {
    const operation = action === "cancel" ? cancellation : mutation;
    if (
      !fresh ||
      operation.busy ||
      operation.pending ||
      version !== run.version
    )
      return;
    const epoch = fence.capture();
    if (!fence.accepts(epoch)) return;
    const body = {
      action,
      expected_version: version,
      ...(action === "steer"
        ? { goal: text.trim() }
        : action === "answer"
          ? { answer: text.trim() }
          : {}),
    };
    await operation.run(
      `/agent-runs/${encodeURIComponent(run.id)}/actions`,
      body,
      () => {
        if (!fence.accepts(epoch)) return;
        if (action === "cancel") setCancelVersion(null);
        else setEditor(null);
        onChanged();
      },
    );
  }
  const actions = runActions(run.state, run.state_reason, run.plan_revision);
  const viewEpoch = fence.capture();
  const feedback = (operation: typeof mutation) => ({
    ...operation,
    busy: operation.busy || !fresh,
    retry: () =>
      fresh && fence.accepts(viewEpoch)
        ? operation.retry()
        : Promise.resolve(false),
  });
  return (
    <article className="agent-detail">
      <h3>{t("Requested result", "请求的结果")}</h3>
      <p className="agent-text">{run.goal}</p>
      {run.voice_origin && <VoiceOriginLabel origin={run.voice_origin} t={t} />}
      <p className="agent-state" role="status">
        {stateLabel(run.state, t)} · {modeLabel(run.mode, t)}
      </p>
      <p className="workspace-hint">
        {t("Run", "运行")}: {run.id} · v{run.version} · {t("Plan", "计划")}{" "}
        {run.plan_revision}
        <br />
        {t("Updated", "更新时间")}: {run.updated_at}
      </p>
      {run.state_reason && (
        <div className="agent-notice">
          <p>{blockLabel(run.state_reason, t)}</p>
          <small>{run.state_reason}</small>
        </div>
      )}
      {run.question && (
        <p className="agent-notice">
          {t("Question", "问题")}: {run.question}
        </p>
      )}
      <p>
        {run.evidence_count} {t("evidence records", "条证据记录")} ·{" "}
        {run.model_calls} {t("model calls recorded", "次已记录模型调用")}
      </p>
      {run.mode === "model" && run.model_call_budget !== undefined && (
        <p className="workspace-hint">
          {t("Model attempts", "模型尝试")}: {run.model_calls} /{" "}
          {run.model_call_budget}
          {run.tool_call_budget !== undefined && (
            <>
              {" "}
              · {t("Tool calls", "工具调用")}: {run.tool_calls ?? 0} /{" "}
              {run.tool_call_budget}
            </>
          )}
        </p>
      )}
      <p className="workspace-hint">
        {t(
          "Completion means the required application checks passed; model-authored conclusions still need your review. Pausing or cancelling does not undo saved files or completed application actions.",
          "完成表示必需的应用检查已通过；模型撰写的结论仍需您审阅。暂停或取消不会撤销已保存文件或已完成应用操作。",
        )}
      </p>
      <div className="workspace-inline-actions">
        {actions
          .filter((x) => x !== "cancel")
          .map((action) => (
            <button
              key={action}
              className="secondary"
              disabled={!fresh || locked || cancelLocked}
              onClick={() =>
                setEditor({
                  action: action as Exclude<RunAction, "cancel">,
                  version: run.version,
                  text: "",
                  question: run.question,
                })
              }
            >
              {actionLabel(action, t)}
            </button>
          ))}
        {actions.includes("cancel") && (
          <button
            className="secondary agent-stop"
            disabled={!fresh || cancelLocked}
            onClick={() => setCancelVersion(run.version)}
          >
            {actionLabel("cancel", t)}
          </button>
        )}
      </div>
      {editor && (
        <fieldset className="agent-control">
          <legend>{actionLabel(editor.action, t)}</legend>
          {editor.action === "answer" && (
            <p className="agent-text">{editor.question}</p>
          )}
          {["steer", "answer"].includes(editor.action) ? (
            <label>
              {editor.action === "answer"
                ? t("Your answer", "您的回答")
                : t(
                    "Revised goal within the existing source and tool scope",
                    "现有来源与工具范围内的新目标",
                  )}
              <textarea
                maxLength={editor.action === "answer" ? 2000 : 4000}
                value={editor.text}
                disabled={locked}
                onChange={(e) => setEditor({ ...editor, text: e.target.value })}
                rows={3}
              />
            </label>
          ) : (
            <p>
              {editor.action === "retry_model"
                ? t(
                    "The previous model call has an unknown remote outcome and may already have been billed. This explicitly permits a NEW model attempt within the remaining run budget and the same approved destination/source scope. It does not repeat application writes.",
                    "之前的模型调用在远端结果未知，可能已产生费用。此操作明确允许在此次运行剩余额度和相同已批准目的地／来源范围内发起新的模型尝试，不会重复应用写入。",
                  )
                : editor.action === "resume"
                  ? t(
                      "Resume uses current permissions and remaining budget; it may make provider calls if this is model work. No additional source or application permission is granted.",
                      "恢复使用当前权限与剩余额度；模型工作可能发起提供商调用，不会新增来源或应用权限。",
                    )
                  : t(
                      "Stop dispatching new work. Any action already sent may still complete and must be reconciled.",
                      "停止派发新工作。已经发出的操作仍可能完成，必须核对结果。",
                    )}
            </p>
          )}
          {editor.version !== run.version && (
            <p role="alert">
              {t(
                "The run changed while this control was open. Close it and review the current version.",
                "打开此操作后运行已变化，请关闭并重新审阅当前版本。",
              )}
            </p>
          )}
          <div className="workspace-inline-actions">
            <button
              className="secondary"
              disabled={locked}
              onClick={() => setEditor(null)}
            >
              {t("Discard this control draft", "放弃此次操作草稿")}
            </button>
            <button
              className="primary"
              disabled={
                !fresh ||
                locked ||
                cancelLocked ||
                editor.version !== run.version ||
                (["steer", "answer"].includes(editor.action) &&
                  !editor.text.trim())
              }
              onClick={() =>
                void perform(editor.action, editor.version, editor.text)
              }
            >
              {t("Apply to this version", "应用于此版本")}
            </button>
          </div>
        </fieldset>
      )}
      <RequestFeedback mutation={feedback(mutation)} t={t} />
      {cancelVersion !== null && (
        <div className="agent-notice" role="alert">
          <p>
            {t(
              "Cancel future work for this run? Completed effects and stored outputs remain. Unknown effects still need verification.",
              "取消此次运行的后续工作？已完成操作和保存输出仍会保留，结果未知的操作仍需核验。",
            )}
          </p>
          {cancelVersion !== run.version && (
            <p>
              {t(
                "The run changed. Choose Cancel work again to review the current version.",
                "运行已变化，请再次选择取消工作以审阅当前版本。",
              )}
            </p>
          )}
          <div className="workspace-inline-actions">
            <button
              className="secondary"
              disabled={cancelLocked}
              onClick={() => setCancelVersion(null)}
            >
              {t("Keep working", "继续工作")}
            </button>
            <button
              className="secondary agent-stop"
              disabled={!fresh || cancelLocked || cancelVersion !== run.version}
              onClick={() => void perform("cancel", cancelVersion)}
            >
              {t("Confirm cancellation", "确认取消")}
            </button>
          </div>
        </div>
      )}
      <RequestFeedback mutation={feedback(cancellation)} t={t} />
      <RunApplicationJobs
        jobs={detail.application_jobs ?? []}
        active={[
          "queued",
          "running",
          "waiting_review",
          "waiting_effect",
        ].includes(run.state)}
        t={t}
        fence={fence}
        fresh={fresh && !mutation.busy && !cancellation.busy}
        onChanged={onChanged}
      />

      <section>
        <h4>{t("Plan and observed progress", "计划与实际进展")}</h4>
        {!!run.plan?.length && (
          <ol>
            {run.plan.map((label, index) => (
              <li key={index}>{label}</li>
            ))}
          </ol>
        )}
        {!detail.steps.length ? (
          <p>
            {t(
              "No plan steps have been recorded yet.",
              "尚无已记录的计划步骤。",
            )}
          </p>
        ) : (
          <ol className="agent-steps">
            {detail.steps.map((step) => (
              <li key={step.id}>
                <strong>{step.label}</strong>
                <span>
                  {step.state === "succeeded"
                    ? t("Step completed", "步骤已完成")
                    : stateLabel(step.state, t)}
                </span>
                {step.error && <small>{step.error}</small>}
              </li>
            ))}
          </ol>
        )}
      </section>
      <section>
        <h4>
          {t("Evidence coverage and unmet checks", "证据覆盖与未满足检查")}
        </h4>
        {!!run.outcome_requirements?.required_sections.length && (
          <p>
            {t("Required sections", "必需章节")}:{" "}
            {run.outcome_requirements.required_sections.join(" · ")}
          </p>
        )}
        {run.unmet_requirements?.map((item, index) => (
          <div className="agent-notice" key={index}>
            <p>{blockLabel(item.code, t)}</p>
            <small>{item.evidence_id ?? item.section ?? item.code}</small>
            {item.total_lines !== undefined && (
              <p>
                {t("Covered through line", "已覆盖至行")}{" "}
                {item.covered_through_line ?? 0} / {item.total_lines}
              </p>
            )}
          </div>
        ))}
        {!run.unmet_requirements?.length && (
          <p className="workspace-hint">
            {t(
              "No unmet structural check is currently recorded. This is not a content-quality endorsement.",
              "当前没有记录未满足的结构检查，这不代表内容质量获得认可。",
            )}
          </p>
        )}
        <ul>
          {run.evidence?.map((item) => (
            <li key={item.id}>
              <strong>{item.label}</strong>
              <small>
                {item.id} · {item.at}
              </small>
              {item.coverage.start_line !== undefined && (
                <span>
                  {t("Excerpt lines", "摘录行")}: {item.coverage.start_line}–
                  {item.coverage.end_line} / {item.coverage.total_lines}
                </span>
              )}
              {item.coverage.truncated && (
                <small>{t("Excerpt truncated", "摘录已截断")}</small>
              )}
              {item.local_parser_coverage && (
                <small>
                  {t("Local parser coverage", "本地解析覆盖")}:{" "}
                  {item.local_parser_coverage.start_line}–
                  {item.local_parser_coverage.end_line} ·{" "}
                  {t("not model-reading proof", "不代表模型已阅读")}
                </small>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h4>{t("Calendar and task changes", "日历与事务修改")}</h4>
        {detail.proposals.length ? (
          detail.proposals.map((proposal) => (
            <div className="agent-review" key={proposal.id}>
              <span>
                {proposal.kind} ·{" "}
                {proposal.state
                  ? stateLabel(proposal.state, t)
                  : t("Check current status", "核对当前状态")}
              </span>
              <small>
                {proposal.id}
                {proposal.expires_at
                  ? ` · ${t("Expires", "到期时间")}: ${proposal.expires_at}`
                  : ""}
              </small>
              <button
                className="secondary"
                disabled={
                  !onReviewProposal ||
                  !fresh ||
                  !canReviewProposal(proposal) ||
                  mutation.busy ||
                  cancellation.busy
                }
                onClick={() => {
                  if (fresh && canReviewProposal(proposal))
                    onReviewProposal?.(proposal.id);
                }}
              >
                {t("Open exact review in Assistant", "在助理中打开确切审阅")}
              </button>
            </div>
          ))
        ) : (
          <p>
            {t(
              "No calendar or task changes are proposed.",
              "暂无日历或事务修改提议。",
            )}
          </p>
        )}
      </section>
      {!!run.tool_results?.length && (
        <details>
          <summary>
            {t("Tool activity and result references", "工具活动与结果引用")}
          </summary>
          <p className="workspace-hint">
            {t(
              "These are recorded tool results, not a claim that the whole goal is complete. External responses remain untrusted; inspect the linked review and its evidence.",
              "这些是工具结果记录，不代表整个目标完成。外部响应仍不可信，请检查关联审阅与证据。",
            )}
          </p>
          <ol className="agent-steps">
            {run.tool_results.map((result, index) => (
              <li key={`${result.operation_key}:${index}`}>
                <strong>{result.tool}</strong>
                <span>
                  {result.state === "observed"
                    ? t("Response observed", "已观察响应")
                    : result.state === "verified"
                      ? t("Recorded verification available", "可检查已记录核验")
                      : result.state === "rejected"
                        ? t("Rejected", "已拒绝")
                        : stateLabel(result.state, t)}
                </span>
                <small>{result.reference_id}</small>
              </li>
            ))}
          </ol>
        </details>
      )}
      <RunBrowserJobs
        jobs={detail.browser_jobs ?? []}
        t={t}
        locked={!fresh || mutation.busy || cancellation.busy}
        onReview={onReviewBrowserJob}
      />
      <RunConnectorResults
        results={run.tool_results ?? []}
        t={t}
        locked={!fresh || mutation.busy || cancellation.busy}
        onReview={onReviewConnectorIntent}
      />
      <ArtifactList artifacts={detail.artifacts} t={t} fence={fence} />
      <details>
        <summary>{t("Activity history", "活动历史")}</summary>
        <ol className="agent-events">
          {detail.events.map((event) => (
            <li key={event.sequence}>
              <time>{event.at}</time> · {event.kind}
            </li>
          ))}
        </ol>
        <p className="workspace-hint">
          {t(
            "Recorded actions and status only; no private reasoning trace is shown.",
            "仅显示记录的操作与状态，不显示私有推理过程。",
          )}
        </p>
      </details>
    </article>
  );
}
