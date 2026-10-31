import {
  RunApplicationSelection,
  RunApplicationReview,
} from "./RunApplicationSelection";
import type { WorkCapacity } from "./workCapacity";
import { OutputCapacityHint } from "./RetainedCapacity";
import { VoiceOriginLabel } from "../voiceWork/VoiceWorkPanel";
import type { VoiceGoalOrigin } from "../voiceWork/types";
import { useEffect, useRef, useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import { modeLabel } from "./labels";
import { RequestFeedback } from "./RequestFeedback";
import { PublicCapture } from "./PublicCapture";
import { SourceUpload } from "./SourceUpload";
import { SourcePreview } from "./SourcePreview";
import { RunBrowserSelection } from "./RunBrowserSelection";
import { RunConnectorSelection } from "./RunConnectorSelection";
import { RunContextSelection } from "./RunContextSelection";
import {
  budgetLimit,
  newRunDraft,
  prepareRun,
  exactTaskHandoffReady,
} from "./types";
import type {
  AgentRun,
  RunCreateInput,
  RunDraft,
  RunScope,
  SourceRecord,
} from "./types";

export function RunComposer({
  t,
  scope,
  fence,
  fresh,
  onClose,
  onCreated,
  onRefresh,
  initialGoal = "",
  voiceOrigin,
  exactTaskIds,
  capacity = null,
}: {
  t: Translate;
  scope: RunScope;
  fence: ResponseFence;
  fresh: boolean;
  onClose: () => void;
  onCreated: (run: AgentRun) => void;
  onRefresh: () => void;
  initialGoal?: string;
  voiceOrigin?: VoiceGoalOrigin;
  exactTaskIds?: string[];
  capacity?: WorkCapacity | null;
}) {
  const mountEpoch = useRef(fence.capture());
  const [originExpired, setOriginExpired] = useState(
    () => !!voiceOrigin && Date.parse(voiceOrigin.expires_at) <= Date.now(),
  );
  useEffect(() => {
    if (!voiceOrigin) return;
    const timer = setTimeout(
      () => setOriginExpired(true),
      Math.max(0, Date.parse(voiceOrigin.expires_at) - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [voiceOrigin]);
  const [draft, setDraft] = useState<RunDraft>(() => ({
    ...newRunDraft(initialGoal),
    ...(exactTaskIds ? { task_ids: [...exactTaskIds] } : {}),
    ...(voiceOrigin ? { voice_origin_ref: voiceOrigin.voice_origin_ref } : {}),
    mode:
      !voiceOrigin &&
      !exactTaskIds &&
      initialGoal &&
      scope.modes.includes("model")
        ? "model"
        : "deterministic",
  }));
  const [review, setReview] = useState<{
    input: RunCreateInput;
    scope: RunScope;
  } | null>(null);
  const [uploadDraft, setUploadDraft] = useState(false);
  const [captureDraft, setCaptureDraft] = useState(false);
  const [preview, setPreview] = useState<SourceRecord | null>(null);
  const mutation = usePrivateMutation();
  const locked = mutation.busy || mutation.pending;
  const handoffReady =
    !exactTaskIds || exactTaskHandoffReady(exactTaskIds, draft, scope);
  const input = handoffReady ? prepareRun(draft, scope) : null;
  const scopeChanged =
    !!review && review.input.scope_revision !== scope.scope_revision;
  const dirty =
    JSON.stringify(draft) !== JSON.stringify(newRunDraft()) ||
    mutation.pending ||
    uploadDraft ||
    captureDraft;
  useDraftGuard(dirty, mutation.busy);
  useEffect(() => {
    setDraft((old) => ({
      ...old,
      share: false,
      retain: false,
      allow_application_jobs: false,
      application_source_ids: [],
      browser_public_only: false,
      share_connector_results_with_provider: false,
      personal_context: {
        ...old.personal_context,
        retain_derived_context: false,
      },
    }));
  }, [scope.scope_revision]);
  const change = <K extends keyof RunDraft>(key: K, value: RunDraft[K]) =>
    setDraft((old) => ({ ...old, [key]: value }));
  function toggle(
    key: "source_ids" | "task_ids" | "event_ids",
    id: string,
    checked: boolean,
  ) {
    setDraft((old) => ({
      ...old,
      [key]: checked ? [...old[key], id] : old[key].filter((x) => x !== id),
      retain: false,
      share: false,
    }));
  }
  async function start() {
    if (!fresh || !review || scopeChanged || locked || !handoffReady) return;
    if (voiceOrigin && Date.parse(voiceOrigin.expires_at) <= Date.now()) return;
    const epoch = mountEpoch.current;
    if (!fence.accepts(epoch)) return;
    await mutation.run<{ run: AgentRun }>(
      "/agent-runs",
      review.input,
      ({ run }) => {
        if (fence.accepts(epoch)) onCreated(run);
      },
    );
  }
  const viewEpoch = mountEpoch.current;
  return (
    <Modal
      title={t("New work", "新工作")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      wide
      busy={mutation.busy}
      dirty={dirty}
    >
      <div className="agent-composer">
        {capacity?.artifacts.count.remaining != null &&
          capacity.artifacts.count.remaining < 2 && (
            <p className="error-message" role="alert">
              {t(
                "Not enough storage for a new report.",
                "没有足够空间保存新报告。",
              )}
            </p>
          )}
        {exactTaskIds && (
          <div className="agent-notice">
            <p>
              {t(
                "Uses the current records of the selected tasks.",
                "使用所选事务的当前记录。",
              )}
            </p>
            {!handoffReady && (
              <p role="alert">
                {t(
                  "An enrolled task is unavailable or the exact selection changed. Starting is blocked; no ID is silently removed. Close this draft and review a new choice.",
                  "已关注事务不可用或确切选择已变化，不能开始；不会自动移除ID。请关闭此草稿并审阅新的选择。",
                )}
              </p>
            )}
            <ul>
              {exactTaskIds.map((id) => (
                <li key={id}>
                  {scope.tasks.find((task) => task.id === id)?.title ??
                    t("Unavailable task", "事务不可用")}
                </li>
              ))}
            </ul>
          </div>
        )}

        {originExpired && (
          <p role="status">
            {mutation.pending
              ? t(
                  "The temporary voice reference expired. Check whether work started; only the original exact request can recover a committed run.",
                  "临时语音引用已到期。请核对工作是否已开始，仅原来的同一请求可恢复已创建运行。",
                )
              : t(
                  "The temporary voice reference expired. Starting is blocked. Select and review a new snapshot; this goal is not silently converted to typed work.",
                  "临时语音引用已到期，不能开始。请重新选择并审阅快照，不会自动转为普通文字工作。",
                )}
          </p>
        )}
        {voiceOrigin && (
          <>
            <VoiceOriginLabel origin={voiceOrigin} t={t} />
            <p>
              {t(
                "Save this reviewed goal and its work results locally. This does not save the full voice conversation or raw audio.",
                "在本地保存此审阅后的目标及工作结果，不保存完整语音交谈或原始录音。",
              )}
            </p>
            {draft.mode === "model" && (
              <p>
                {t(
                  "The work provider may differ from the voice provider. Sharing this goal and selected context requires the separate exact-destination review below.",
                  "工作提供商可能与语音提供商不同。共享此目标及所选上下文，需要下方独立的确切目的地审阅。",
                )}
              </p>
            )}
          </>
        )}
        {!fresh && (
          <p className="agent-notice" role="status">
            {t(
              "The current scope could not be refreshed. Your draft and retry data are preserved. Refresh must succeed before starting, retrying or uploading a source.",
              "未能刷新当前范围，草稿与重试资料已保留。刷新成功前，不能开始、重试或上传来源。",
            )}
          </p>
        )}
        {review ? (
          <>
            <h3>{t("Review work", "确认工作")}</h3>
            <p className="agent-text">{review.input.goal}</p>
            <p>{modeLabel(review.input.mode, t)}</p>
            <ul>
              {review.scope.sources
                .filter((x) => review.input.source_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("File", "文件")}: {x.name}{" "}
                  </li>
                ))}
              {review.scope.tasks
                .filter((x) => review.input.task_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("Task", "事务")}: {x.title}{" "}
                  </li>
                ))}
              {review.scope.events
                .filter((x) => review.input.event_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("Calendar", "日历")}: {x.title} {x.start_local}–
                    {x.end_local} {x.timezone}
                  </li>
                ))}
              {review.scope.browser?.sources
                .filter((source) =>
                  review.input.browser_source_ids.includes(source.id),
                )
                .map((source) => (
                  <li key={source.id}>
                    {t("Public browser source", "公开浏览器来源")}:{" "}
                    {source.label}
                    <small>{source.url}</small>
                  </li>
                ))}
              {review.scope.connectors?.tools
                .filter((tool) =>
                  review.input.connector_tool_ids.includes(tool.tool_id),
                )
                .map((tool) => (
                  <li key={tool.tool_id}>
                    {t("Proposable connector tool", "可提议调用的连接工具")}:{" "}
                    {tool.connector_id} · {tool.tool_name}
                    <small>{tool.endpoint}</small>
                    <small>{tool.destination_scope}</small>
                  </li>
                ))}
            </ul>
            <RunApplicationReview
              input={review.input}
              scope={review.scope}
              t={t}
            />
            {review.input.required_sections.length > 0 && (
              <p>
                {t("Required report sections", "必需报告章节")}:{" "}
                {review.input.required_sections.join(" · ")}
              </p>
            )}
            {review.input.source_ids.length +
              review.input.task_ids.length +
              review.input.event_ids.length +
              review.input.browser_source_ids.length +
              review.input.connector_tool_ids.length ===
              0 && (
              <p>
                {t(
                  "No saved sources selected. The run must disclose missing evidence.",
                  "未选择保存的来源，运行必须说明证据缺失。",
                )}
              </p>
            )}
            {review.input.mode === "model" && (
              <div className="agent-notice">
                <strong>{t("Shared with", "发送给")}</strong>
                {review.scope.destinations
                  .filter((x) => x.id === review.input.provider_destination_id)
                  .map((x) => (
                    <p key={x.id}>
                      {x.provider}
                      <small>{x.endpoint}</small>
                    </p>
                  ))}
                <p>
                  {t(
                    "This AI receives your goal, selected content and work results.",
                    "此AI会收到目标、所选内容和工作结果。",
                  )}
                </p>
                <p className="workspace-hint">
                  {t(
                    "AI requests may incur charges; the attempt limit is not a spending cap.",
                    "AI请求可能计费，次数上限不等于金额上限。",
                  )}
                </p>
                <details className="workspace-details">
                  <summary>{t("Usage limits", "用量上限")}</summary>
                  <p>
                    {t("Run limits", "运行上限")}:{" "}
                    {review.input.model_call_budget}{" "}
                    {t("model attempts", "次模型尝试")} ·{" "}
                    {review.input.tool_call_budget}{" "}
                    {t("tool calls", "次工具调用")}
                  </p>
                </details>
                {review.input.browser_source_ids.length > 0 && (
                  <p>
                    {t(
                      "Selected public pages may be read and their excerpts shared with this provider. A public-only brief can be prepared for https://stackedit.io/app, but no editor action is approved by starting this run. Open each linked browser review before approving its exact content and export.",
                      "可读取所选公开页面，并向此提供商共享摘录。可为 https://stackedit.io/app 准备仅含公开内容的简报，但开始此次运行不批准编辑器动作。请打开每项关联浏览器审阅后，再批准确切内容与导出。",
                    )}
                  </p>
                )}
                {review.input.connector_tool_ids.length > 0 && (
                  <p>
                    {t(
                      "Each selected connector call, including reads, still requires exact-argument approval. Its public or synthetic response may then be sent to this exact model provider so work can continue. A remote response is not independently verified completion.",
                      "每项所选连接工具调用（包括读取）仍需批准确切参数。返回的公开或虚构响应随后可发送至此确切模型提供商，使工作继续。远端响应不等于已独立核验完成。",
                    )}
                  </p>
                )}
                {review.input.personal_context && (
                  <div>
                    <strong>
                      {t(
                        "Explicitly selected personal context",
                        "明确选择的个人上下文",
                      )}
                    </strong>
                    <ul>
                      {review.scope.personal_context?.memories
                        .filter((memory) =>
                          review.input.personal_context!.memory_ids.includes(
                            memory.id,
                          ),
                        )
                        .map((memory) => (
                          <li key={memory.id}>
                            {memory.summary} · v{memory.version}
                          </li>
                        ))}
                    </ul>
                    {review.scope.personal_context?.conversations
                      .filter(
                        (thread) =>
                          thread.id ===
                          review.input.personal_context!.conversation_id,
                      )
                      .map((thread) => (
                        <p key={thread.id}>
                          {thread.title} ·{" "}
                          {t(
                            "up to 12 eligible messages present at start",
                            "开始时已有的最多12条可用消息",
                          )}
                        </p>
                      ))}
                    <p>
                      {t(
                        "This context is not evidence or tool permission. Retained outputs may repeat it; later forgetting does not erase old outputs or provider copies.",
                        "这些上下文不是证据或工具许可。保留输出可能重复其中内容，之后忘记不会删除旧输出或提供商副本。",
                      )}
                    </p>
                  </div>
                )}
                <p>
                  {review.input.allow_mutation_proposals
                    ? t(
                        "Calendar and task changes need your approval.",
                        "日历与事务修改需由你确认。",
                      )
                    : t(
                        "Calendar and task changes are off.",
                        "日历与事务修改已关闭。",
                      )}
                </p>
              </div>
            )}
            <p className="workspace-hint">
              {t(
                "Work is saved in this workspace. Deletion is not available yet.",
                "工作保存在此工作空间，目前尚不能删除。",
              )}
            </p>
            {scopeChanged && (
              <p role="alert" className="error-message">
                {t(
                  "The available scope changed. Return to selection and review it again before starting.",
                  "可用范围已变化，请返回选择并重新审阅后再开始。",
                )}
              </p>
            )}
            {voiceOrigin && mutation.pending && (
              <p role="status">
                {t(
                  "Check whether work started. Retry only the same request; reconnecting voice is not needed.",
                  "请核对工作是否已开始。仅重试同一请求，无需重连语音。",
                )}
              </p>
            )}
            <RequestFeedback
              mutation={{
                ...mutation,
                busy: mutation.busy || !fresh,
                retry: () =>
                  fresh && fence.accepts(viewEpoch)
                    ? mutation.retry()
                    : Promise.resolve(false),
              }}
              t={t}
            />
            <div className="workspace-inline-actions">
              <button
                className="secondary"
                disabled={locked}
                onClick={() => setReview(null)}
              >
                {t("Back", "返回")}
              </button>
              <button
                className="primary"
                disabled={
                  !fresh ||
                  locked ||
                  scopeChanged ||
                  originExpired ||
                  !handoffReady
                }
                onClick={() => void start()}
              >
                {mutation.busy
                  ? t("Starting…", "正在开始…")
                  : t("Start work", "开始工作")}
              </button>
            </div>
          </>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (
                fresh &&
                input &&
                !uploadDraft &&
                !captureDraft &&
                !originExpired
              )
                setReview({ input, scope });
            }}
          >
            <label>
              {t("What should Alice do?", "想让 Alice 做什么？")}
              <textarea
                required
                maxLength={4000}
                value={draft.goal}
                onChange={(e) => change("goal", e.target.value)}
                rows={3}
                placeholder={t(
                  "Describe the result you want…",
                  "描述你想得到的结果…",
                )}
              />
            </label>
            <label>
              {t("Mode", "方式")}
              <select
                disabled={!!exactTaskIds}
                value={draft.mode}
                onChange={(e) =>
                  setDraft((old) => ({
                    ...old,
                    mode: e.target.value as RunDraft["mode"],
                    destination: "",
                    share: false,
                    retain: false,
                    allow_mutation_proposals: false,
                    allow_application_jobs: false,
                    application_source_ids: [],
                    browser_source_ids: [],
                    browser_public_only: false,
                    connector_tool_ids: [],
                    share_connector_results_with_provider: false,
                    personal_context: {
                      memory_ids: [],
                      conversation_id: null,
                      retain_derived_context: false,
                    },
                  }))
                }
              >
                {scope.modes.includes("deterministic") && (
                  <option value="deterministic">
                    {t("Local report", "本地报告")}
                  </option>
                )}
                {scope.modes.includes("model") && (
                  <option value="model">
                    {t("Plan with AI", "交给AI处理")}
                  </option>
                )}
              </select>
            </label>
            {!scope.modes.includes("model") && (
              <p className="workspace-hint">
                {t("AI planning is not configured.", "尚未配置AI规划。")}
              </p>
            )}
            {draft.connector_tool_ids.length > 0 && (
              <p className="agent-notice">
                {t(
                  "Connector work is limited to public or synthetic data. Local files, tasks, calendar and personal context cannot be added to this run; public browser sources remain optional.",
                  "连接工具工作仅限公开或虚构资料。此次运行不能加入本地文件、事务、日历或个人上下文；可选择公开浏览器来源。",
                )}
              </p>
            )}
            <fieldset disabled={!!exactTaskIds}>
              <legend>{t("Files", "文件")}</legend>
              <div className="agent-choices">
                {scope.sources.map((x) => (
                  <div className="agent-source-choice" key={x.id}>
                    <label className="agent-check">
                      <input
                        type="checkbox"
                        checked={draft.source_ids.includes(x.id)}
                        disabled={
                          !draft.source_ids.includes(x.id) &&
                          (x.status !== "verified" ||
                            draft.connector_tool_ids.length > 0 ||
                            draft.source_ids.length >= 12)
                        }
                        onChange={(e) =>
                          toggle("source_ids", x.id, e.target.checked)
                        }
                      />
                      <span>
                        {x.name}
                        <small>
                          {x.format} · {x.byte_count.toLocaleString()}{" "}
                          {t("bytes", "字节")} · {x.id}
                        </small>
                        {x.status !== "verified" && (
                          <small>
                            {t(
                              "Stored bytes are not verified; this source cannot be selected. Inspect the upload result and refresh.",
                              "保存字节尚未核验，不能选择此来源。请检查上传结果并刷新。",
                            )}
                          </small>
                        )}
                      </span>
                    </label>
                    <button
                      type="button"
                      className="secondary"
                      disabled={!fresh || x.status !== "verified"}
                      onClick={() => setPreview(x)}
                    >
                      {t("Preview", "预览")}
                    </button>
                  </div>
                ))}
              </div>
              <SourceUpload
                t={t}
                fence={fence}
                fresh={fresh && !exactTaskIds}
                capacity={capacity}
                onUploaded={() => onRefresh()}
                onDraftChange={setUploadDraft}
              />
              <PublicCapture
                t={t}
                fence={fence}
                epoch={viewEpoch}
                fresh={fresh && !exactTaskIds}
                onDraftChange={setCaptureDraft}
                onChanged={onRefresh}
              />
            </fieldset>
            <fieldset>
              <legend>{t("Tasks", "事务")}</legend>
              <div className="agent-choices">
                {scope.tasks.map((x) => (
                  <label key={x.id} className="agent-check">
                    <input
                      type="checkbox"
                      checked={draft.task_ids.includes(x.id)}
                      disabled={
                        !!exactTaskIds ||
                        (!draft.task_ids.includes(x.id) &&
                          (draft.task_ids.length >= 10 ||
                            draft.connector_tool_ids.length > 0))
                      }
                      onChange={(e) =>
                        toggle("task_ids", x.id, e.target.checked)
                      }
                    />
                    <span>{x.title}</span>
                  </label>
                ))}
              </div>
              {!scope.tasks.length && (
                <p>{t("No tasks yet.", "还没有事务。")}</p>
              )}
            </fieldset>
            {(scope.events.length > 0 || draft.event_ids.length > 0) && (
              <fieldset disabled={!!exactTaskIds}>
                <legend>{t("Calendar", "日历")}</legend>
                <div className="agent-choices">
                  {scope.events.map((x) => (
                    <label key={x.id} className="agent-check">
                      <input
                        type="checkbox"
                        checked={draft.event_ids.includes(x.id)}
                        disabled={
                          !draft.event_ids.includes(x.id) &&
                          (draft.event_ids.length >= 10 ||
                            draft.connector_tool_ids.length > 0)
                        }
                        onChange={(e) =>
                          toggle("event_ids", x.id, e.target.checked)
                        }
                      />
                      <span>
                        {x.title}
                        <small>
                          {x.start_local}–{x.end_local} {x.timezone}
                        </small>
                      </span>
                    </label>
                  ))}
                </div>
                {!scope.events.length && (
                  <p>
                    {t("No available calendar records.", "暂无可用日历记录。")}
                  </p>
                )}
              </fieldset>
            )}

            {draft.mode === "model" && (
              <RunApplicationSelection
                draft={draft}
                scope={scope}
                t={t}
                onChange={setDraft}
              />
            )}
            <details className="workspace-details">
              <summary>{t("More options", "更多选项")}</summary>
              <label>
                {t("Report headings (optional)", "报告章节（可选）")}
                <textarea
                  rows={2}
                  maxLength={1287}
                  value={draft.required_sections}
                  onChange={(e) => change("required_sections", e.target.value)}
                />
              </label>
              {draft.mode === "model" && (
                <div className="workspace-form-grid">
                  <label>
                    {t("Maximum model attempts", "最多模型尝试次数")}
                    <input
                      type="number"
                      min={1}
                      max={budgetLimit(scope, "model")}
                      step={1}
                      required
                      value={draft.model_call_budget}
                      onChange={(event) =>
                        change("model_call_budget", Number(event.target.value))
                      }
                    />
                  </label>
                  <label>
                    {t(
                      "Maximum application / browser / connector tool calls",
                      "最多应用／浏览器／连接工具调用次数",
                    )}
                    <input
                      type="number"
                      min={1}
                      max={budgetLimit(scope, "tool")}
                      step={1}
                      required
                      value={draft.tool_call_budget}
                      onChange={(event) =>
                        change("tool_call_budget", Number(event.target.value))
                      }
                    />
                  </label>
                  <p className="workspace-hint">
                    {t(
                      "Calls that fail or have an unknown result still use the run allowance. These limits do not set a currency budget or approve an application action.",
                      "失败或结果未知的调用仍占用运行额度。这些上限不设定货币预算，也不批准应用操作。",
                    )}
                  </p>
                </div>
              )}
              {draft.mode === "model" &&
                (scope.browser?.ready ||
                  draft.browser_source_ids.length > 0) && (
                  <RunBrowserSelection
                    draft={draft}
                    scope={scope}
                    t={t}
                    onChange={setDraft}
                  />
                )}
              {draft.mode === "model" &&
                ((scope.connectors?.tools.length ?? 0) > 0 ||
                  draft.connector_tool_ids.length > 0) && (
                  <RunConnectorSelection
                    draft={draft}
                    scope={scope}
                    t={t}
                    onChange={setDraft}
                  />
                )}
              {draft.mode === "model" &&
                ((scope.personal_context?.memories.length ?? 0) > 0 ||
                  (scope.personal_context?.conversations.length ?? 0) > 0) && (
                  <RunContextSelection
                    draft={draft}
                    scope={scope}
                    t={t}
                    onChange={setDraft}
                  />
                )}
              <OutputCapacityHint
                value={capacity}
                t={t}
                deterministic={draft.mode === "deterministic"}
              />
            </details>
            {draft.mode === "model" && (
              <fieldset>
                <legend>{t("AI & permissions", "AI与权限")}</legend>
                <label>
                  {t("AI provider", "AI服务")}
                  <select
                    required
                    value={draft.destination}
                    onChange={(e) => {
                      setDraft((old) => ({
                        ...old,
                        destination: e.target.value,
                        share: false,
                        retain: false,
                        share_connector_results_with_provider: false,
                        personal_context: {
                          ...old.personal_context,
                          retain_derived_context: false,
                        },
                      }));
                    }}
                  >
                    <option value="">{t("Choose AI", "选择AI")}</option>
                    {scope.destinations
                      .filter((x) => x.kind === "text")
                      .map((x) => (
                        <option key={x.id} value={x.id}>
                          {x.provider} · {x.endpoint}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="agent-check">
                  <input
                    type="checkbox"
                    checked={draft.allow_mutation_proposals}
                    onChange={(e) =>
                      change("allow_mutation_proposals", e.target.checked)
                    }
                  />
                  {t(
                    "Suggest calendar and task changes for my review",
                    "允许提出日历与事务修改，交给我确认",
                  )}
                </label>
                <label className="agent-check">
                  <input
                    type="checkbox"
                    checked={draft.share}
                    onChange={(e) => change("share", e.target.checked)}
                  />
                  {t(
                    "Share this goal and selected content with this AI",
                    "向此AI发送目标与所选内容",
                  )}
                </label>
                {!scope.business_context_allowed &&
                  (draft.task_ids.length > 0 || draft.event_ids.length > 0) && (
                    <p role="alert">
                      {t(
                        "Sharing saved tasks/calendar with the provider is disabled. Review Assistant context settings or use local compilation.",
                        "向提供商共享保存的事务／日历已关闭，请核对助理上下文设置，或使用本地整理。",
                      )}
                    </p>
                  )}
              </fieldset>
            )}
            <div className="work-submit">
              {draft.source_ids.length +
                draft.task_ids.length +
                draft.event_ids.length +
                draft.browser_source_ids.length +
                draft.connector_tool_ids.length ===
                0 && (
                <p role="status">
                  {t(
                    "Choose a file, task or other source.",
                    "请选择文件、事务或其他来源。",
                  )}
                </p>
              )}
              <p className="workspace-hint">
                {t(
                  "Saved work cannot be deleted yet.",
                  "目前尚不能删除已保存的工作。",
                )}
              </p>
              <label className="agent-check">
                <input
                  type="checkbox"
                  checked={draft.retain}
                  onChange={(e) => change("retain", e.target.checked)}
                />
                {t(
                  "Save this work, its records and files in my workspace",
                  "在工作空间保留这项工作的记录和文件",
                )}
              </label>
              {(uploadDraft || captureDraft) && (
                <p className="workspace-hint">
                  {t(
                    "Finish the upload, clear the unsent source/capture draft, or recover the original capture operation before reviewing this run.",
                    "请完成上传、清除未发送的来源／采集草稿，或恢复原采集操作后，再审阅此次运行。",
                  )}
                </p>
              )}
              <button
                className="primary"
                disabled={
                  !fresh ||
                  !input ||
                  uploadDraft ||
                  captureDraft ||
                  originExpired
                }
              >
                {t("Review", "查看并确认")}
              </button>
            </div>
          </form>
        )}
      </div>
      {preview && (
        <SourcePreview
          source={preview}
          t={t}
          fence={fence}
          onClose={() => setPreview(null)}
        />
      )}
    </Modal>
  );
}
