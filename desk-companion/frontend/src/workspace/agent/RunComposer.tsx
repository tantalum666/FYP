import { useEffect, useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import { modeLabel } from "./labels";
import { RequestFeedback } from "./RequestFeedback";
import { SourceUpload } from "./SourceUpload";
import { SourcePreview } from "./SourcePreview";
import { newRunDraft, prepareRun, selectedBytes } from "./types";
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
  onClose,
  onCreated,
  onRefresh,
}: {
  t: Translate;
  scope: RunScope;
  fence: ResponseFence;
  onClose: () => void;
  onCreated: (run: AgentRun) => void;
  onRefresh: () => void;
}) {
  const [draft, setDraft] = useState(newRunDraft);
  const [review, setReview] = useState<{
    input: RunCreateInput;
    scope: RunScope;
  } | null>(null);
  const [uploadDraft, setUploadDraft] = useState(false);
  const [preview, setPreview] = useState<SourceRecord | null>(null);
  const mutation = usePrivateMutation();
  const locked = mutation.busy || mutation.pending;
  const input = prepareRun(draft, scope);
  const scopeChanged =
    !!review && review.input.scope_revision !== scope.scope_revision;
  const dirty =
    JSON.stringify(draft) !== JSON.stringify(newRunDraft()) || mutation.pending;
  useDraftGuard(dirty, mutation.busy);
  useEffect(() => {
    setDraft((old) => ({ ...old, share: false, retain: false }));
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
    if (!review || scopeChanged || locked) return;
    const epoch = fence.capture();
    if (!fence.accepts(epoch)) return;
    await mutation.run<{ run: AgentRun }>(
      "/agent-runs",
      review.input,
      ({ run }) => {
        if (fence.accepts(epoch)) onCreated(run);
      },
    );
  }
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
            </ul>
            {review.input.required_sections.length > 0 && (
              <p>
                {t("Required report sections", "必需报告章节")}:{" "}
                {review.input.required_sections.join(" · ")}
              </p>
            )}
            {review.input.source_ids.length +
              review.input.task_ids.length +
              review.input.event_ids.length ===
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
            <RequestFeedback mutation={mutation} t={t} />
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
                disabled={locked || scopeChanged}
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
              if (input && !uploadDraft) setReview({ input, scope });
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
                value={draft.mode}
                onChange={(e) =>
                  setDraft((old) => ({
                    ...old,
                    mode: e.target.value as RunDraft["mode"],
                    destination: "",
                    share: false,
                    retain: false,
                    allow_mutation_proposals: false,
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
            <fieldset>
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
                      disabled={x.status !== "verified"}
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
                onUploaded={() => onRefresh()}
                onDraftChange={setUploadDraft}
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
                        !draft.task_ids.includes(x.id) &&
                        draft.task_ids.length >= 10
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
            <fieldset>
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
                        draft.event_ids.length >= 10
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
                "Select at least one evidence item. Model mode allows up to 10 selected files/tasks/calendar records combined.",
                "至少选择一项证据。模型模式下文件／事务／日历记录合计最多10项。",
              )}
            </p>
            {draft.mode === "model" && (
              <fieldset>
                <legend>
                  {t("Provider and allowed use", "提供商与允许用途")}
                </legend>
                <label>
                  {t("Exact provider destination", "确切提供商目的地")}
                  <select
                    required
                    value={draft.destination}
                    onChange={(e) => {
                      change("destination", e.target.value);
                      change("share", false);
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
                "Outputs: a Markdown work report and CSV evidence register. At most two plan versions / four artifacts, 256 KiB each / 1 MiB per run; 100 retained runs. No deletion control in this version. Saved bytes and valid structure do not establish factual accuracy; inspect the results.",
                "输出为Markdown工作报告和CSV证据表。最多两个计划版本／4个文件，每个256 KiB、每次运行合计1 MiB；保留运行上限100项。本版尚无删除入口。字节保存和结构正确不代表事实准确，请检查结果。",
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
            {uploadDraft && (
              <p className="workspace-hint">
                {t(
                  "Finish the upload or clear its selection before reviewing this run.",
                  "请完成上传或清除文件选择后，再审阅此次运行。",
                )}
              </p>
            )}
            <button className="primary" disabled={!input || uploadDraft}>
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
