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
  selectedBytes,
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
      title={t("Start persistent work", "开始持续工作")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      wide
      busy={mutation.busy}
      dirty={dirty}
    >
      <div className="agent-composer">
        <OutputCapacityHint
          value={capacity}
          t={t}
          deterministic={draft.mode === "deterministic"}
        />
        {exactTaskIds && (
          <div className="agent-notice">
            <p>
              {t(
                "This handoff compiles exactly the enrolled tasks using current records. It is separate from acknowledgment and does not reconstruct historical values. Scope is refreshed; retention still needs your choice.",
                "此移交使用当前记录整理已关注的确切事务，与已查看确认独立，也不会重建历史数值。范围已刷新，保留仍需你选择。",
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
                <li key={id}>{id}</li>
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
            <h3>
              {t("Review the goal and exact scope", "核对目标与确切范围")}
            </h3>
            <p className="agent-text">{review.input.goal}</p>
            <p>{modeLabel(review.input.mode, t)}</p>
            <ul>
              {review.scope.sources
                .filter((x) => review.input.source_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("File", "文件")}: {x.name}{" "}
                    <small>
                      {x.id} · {x.sha256}
                    </small>
                  </li>
                ))}
              {review.scope.tasks
                .filter((x) => review.input.task_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("Task", "事务")}: {x.title}{" "}
                    <small>
                      {x.id} · v{x.version}
                    </small>
                  </li>
                ))}
              {review.scope.events
                .filter((x) => review.input.event_ids.includes(x.id))
                .map((x) => (
                  <li key={x.id}>
                    {t("Calendar", "日历")}: {x.title} {x.start_local}–
                    {x.end_local} {x.timezone}
                    <small>
                      {x.id} · v{x.version}
                    </small>
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
                <strong>{t("Data destination", "数据目的地")}</strong>
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
                    "The goal and selected source text may be sent to this destination to plan and produce your work. Task/calendar sharing also requires the existing business-context permission. No account-wide data, screenshots or raw voice recording are granted here.",
                    "目标及所选来源文本可发送至此目的地，用于规划和完成工作。事务／日历共享还需既有业务上下文许可；此处不授权全部账号数据、截图或原始录音。",
                  )}
                </p>
                <p>
                  {t("Run limits", "运行上限")}:{" "}
                  {review.input.model_call_budget}{" "}
                  {t("model attempts", "次模型尝试")} ·{" "}
                  {review.input.tool_call_budget}{" "}
                  {t("tool calls", "次工具调用")}
                </p>
                <p className="workspace-hint">
                  {t(
                    "These are attempt limits, not a monetary cap. Unknown provider calls may have been billed and need explicit review before another attempt.",
                    "这是尝试次数上限，不是金额上限。结果未知的提供商调用可能已计费，再次尝试前需要明确审阅。",
                  )}
                </p>
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
                        "May propose selected task/calendar changes for your later exact review; cannot save them automatically.",
                        "可提出所选事务／日历的修改草稿，之后仍需逐项审阅，不能自动保存。",
                      )
                    : t(
                        "Application change proposals are not authorized for this run.",
                        "此次运行未授权提出应用修改草稿。",
                      )}
                </p>
              </div>
            )}
            <p className="workspace-hint">
              {t(
                "Goals, selected source references, progress and outputs are retained on this server. This does not enable chat-history retention. Closing this panel does not cancel work; signing out or hiding private content can block it. No external notifications are sent.",
                "目标、所选来源引用、进展及输出会保留在此服务端；不会因此启用聊天记录保留。关闭面板不会取消工作，退出登录或隐藏私人内容可能阻止运行。不会发送外部通知。",
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
                {t("Back to selection", "返回选择")}
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
                  : t("Start this persistent work", "开始此次持续工作")}
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
              {t("Requested result", "希望得到的结果")}
              <textarea
                required
                maxLength={4000}
                value={draft.goal}
                onChange={(e) => change("goal", e.target.value)}
                rows={4}
                placeholder={t(
                  "Compare the selected requirements and produce a sourced report and action list",
                  "比较所选需求，生成附来源的报告与行动清单",
                )}
              />
            </label>
            <label>
              {t(
                "Required report section titles (optional, one per line, up to 8 × 160 characters)",
                "必需报告章节标题（可选，每行一项，最多8项，每项160字）",
              )}
              <textarea
                rows={2}
                maxLength={1287}
                value={draft.required_sections}
                onChange={(e) => change("required_sections", e.target.value)}
              />
            </label>
            <label>
              {t("Working mode", "工作模式")}
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
                    {t(
                      "Local evidence compilation · fixed workflow",
                      "本地证据整理 · 固定流程",
                    )}
                  </option>
                )}
                {scope.modes.includes("model") && (
                  <option value="model">
                    {t(
                      "Configured model · bounded adaptive work",
                      "已配置模型 · 有界自适应工作",
                    )}
                  </option>
                )}
              </select>
            </label>
            <p className="workspace-hint">
              {draft.mode === "deterministic"
                ? t(
                    "A fixed local workflow collects selected records and produces a work package. It does not interpret arbitrary goals or call an AI provider.",
                    "固定的本地流程汇集所选记录并生成工作包，不会理解任意目标或调用AI提供商。",
                  )
                : t(
                    "The configured model can plan, read selected evidence, compose reports, ask questions and propose permitted edits. Unsupported goals stop with a block; model text is not proof of completion.",
                    "已配置模型可制定计划、读取所选证据、编写报告、提问及提出获准修改。无法支持的目标会明确阻塞；模型文字不是完成证明。",
                  )}
            </p>
            {!scope.modes.includes("model") && (
              <p className="workspace-hint">
                {t(
                  "Model planning is unavailable until an operator configures an admitted provider. Local compilation remains available.",
                  "操作人员配置获准提供商之前，模型规划不可用；仍可进行本地整理。",
                )}
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
              <legend>
                {t(
                  "Selected files (up to 12 / 4 MiB)",
                  "所选文件（最多12份／4 MiB）",
                )}
              </legend>
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
                      {t("Inspect text", "检查文本")}
                    </button>
                  </div>
                ))}
              </div>
              {scope.sources.length === 0 && (
                <p>
                  {t(
                    "No saved sources. Add a selected file below.",
                    "暂无保存来源，可在下方添加指定文件。",
                  )}
                </p>
              )}
              <p className="workspace-hint">
                {selectedBytes(
                  draft.source_ids,
                  scope.sources,
                ).toLocaleString()}{" "}
                {t("selected bytes", "所选字节")}
              </p>
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
              <legend>
                {t("Selected tasks (up to 10)", "所选事务（最多10项）")}
              </legend>
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
                    <span>
                      {x.title}
                      <small>
                        {x.id} · v{x.version}
                      </small>
                    </span>
                  </label>
                ))}
              </div>
              {!scope.tasks.length && (
                <p>{t("No available tasks.", "暂无可用事务。")}</p>
              )}
            </fieldset>
            <fieldset disabled={!!exactTaskIds}>
              <legend>
                {t(
                  "Selected calendar records (up to 10)",
                  "所选日历记录（最多10项）",
                )}
              </legend>
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
                      <small>
                        {x.id} · v{x.version}
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
            <p className="workspace-hint">
              {t(
                "Select at least one evidence item or a configured connector tool. Model mode allows up to 10 files, tasks, calendar records and public browser sources combined; personal context is not evidence.",
                "至少选择一项证据或已配置连接工具。模型模式下文件、事务、日历记录与公开浏览器来源合计最多10项；个人上下文不属于证据。",
              )}
            </p>
            {draft.mode === "model" && (
              <RunBrowserSelection
                draft={draft}
                scope={scope}
                t={t}
                onChange={setDraft}
              />
            )}
            {draft.mode === "model" && (
              <RunConnectorSelection
                draft={draft}
                scope={scope}
                t={t}
                onChange={setDraft}
              />
            )}
            {draft.mode === "model" && (
              <RunContextSelection
                draft={draft}
                scope={scope}
                t={t}
                onChange={setDraft}
              />
            )}
            {draft.mode === "model" && (
              <fieldset>
                <legend>
                  {t("Provider and allowed use", "提供商与允许用途")}
                </legend>
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
                    "Maximum browser / connector tool calls",
                    "最多浏览器／连接工具调用次数",
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
                <label>
                  {t("Exact provider destination", "确切提供商目的地")}
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
                    <option value="">
                      {t("Choose a destination", "选择目的地")}
                    </option>
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
                    "Allow proposing task/calendar changes for later exact review; never save automatically",
                    "允许提出事务／日历修改，之后仍需逐项审阅；不得自动保存",
                  )}
                </label>
                <label className="agent-check">
                  <input
                    type="checkbox"
                    checked={draft.share}
                    onChange={(e) => change("share", e.target.checked)}
                  />
                  {t(
                    "Send this goal and selected source content to this exact provider for this run",
                    "为此次运行向此确切提供商发送目标与所选来源内容",
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
            <p className="workspace-hint">
              {t(
                "Outputs: a Markdown work report and CSV evidence register. At most two plan versions. No deletion control in this version. Saved bytes and valid structure do not establish factual accuracy; inspect the results.",
                "输出为Markdown工作报告和CSV证据表。最多两个计划版本。本版尚无删除入口。字节保存和结构正确不代表事实准确，请检查结果。",
              )}
            </p>
            <label className="agent-check">
              <input
                type="checkbox"
                checked={draft.retain}
                onChange={(e) => change("retain", e.target.checked)}
              />
              {t(
                "Retain this goal, selected source references, progress and artifacts on this server",
                "在此服务端保留目标、所选来源引用、进展及产物",
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
                !fresh || !input || uploadDraft || captureDraft || originExpired
              }
            >
              {t("Review scope before starting", "开始前审阅范围")}
            </button>
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
