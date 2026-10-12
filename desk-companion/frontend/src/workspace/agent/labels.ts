import { ApiError, errorText } from "../../api";
import type { Translate } from "../../types";
export function stateLabel(state: string, t: Translate) {
  const labels: Record<string, [string, string]> = {
    queued: ["Queued", "排队中"],
    planning: ["Planning", "制定计划"],
    running: ["Working", "运行中"],
    waiting_input: ["Needs your answer", "等待您的回答"],
    waiting_review: ["Needs your review", "等待您的审阅"],
    waiting_effect: ["Waiting for an application result", "等待应用结果"],
    blocked: ["Blocked", "已阻塞"],
    paused: ["Paused", "已暂停"],
    verifying: ["Checking results", "正在核验结果"],
    succeeded: [
      "Output checks passed · quality unreviewed",
      "输出检查通过 · 质量未审阅",
    ],
    partial: ["Partial result", "部分结果"],
    failed: ["Failed", "失败"],
    cancelled: ["Cancelled", "已取消"],
    cancelling: ["Stopping future work", "正在停止后续工作"],
    pending: ["Pending", "待处理"],
    ready: ["Ready", "已就绪"],
    completed: ["Step completed", "步骤已完成"],
    unknown: ["Outcome unknown", "结果未知"],
    skipped: ["Skipped", "已跳过"],
    superseded: ["Replaced by a newer plan", "已被新计划取代"],
    confirmed: ["Confirmed", "已确认"],
    expired: ["Expired", "已过期"],
  };
  return labels[state]
    ? t(...labels[state])
    : t("Unrecognized status", "未知状态") + ` (${state})`;
}
export function modeLabel(mode: string, t: Translate) {
  return mode === "deterministic"
    ? t("Local evidence compilation", "本地证据整理")
    : mode === "model"
      ? t("Configured model", "已配置的模型")
      : t("Unknown mode", "未知模式");
}
export function blockLabel(code: string, t: Translate) {
  const labels: Record<string, [string, string]> = {
    provider_outcome_unknown: [
      "A model request may have completed remotely. Review before resuming; no automatic paid retry.",
      "模型请求可能已在远端完成。请核对后再恢复；不会自动重试付费请求。",
    ],
    source_unavailable: [
      "A selected source is unavailable. Review the source selection.",
      "所选来源不可用，请核对来源。",
    ],
    context_revoked: [
      "Context permission changed. Review current privacy and provider settings.",
      "上下文权限已变化，请核对当前隐私与提供商设置。",
    ],
    budget_exhausted: [
      "This run reached its work budget. Inspect the partial results.",
      "此次运行已达到工作额度，请检查部分结果。",
    ],
    missing_adapter: [
      "The required capability is not installed or admitted.",
      "所需能力未安装或未获准使用。",
    ],
    stale_observation: [
      "The source or application changed. A fresh observation and review are needed.",
      "来源或应用已变化，需要重新观察和审阅。",
    ],
    unresolved_effect: [
      "An application action has an unknown outcome. Verify it before continuing.",
      "应用操作结果未知，请先核验再继续。",
    ],
    expired_review: [
      "The review expired. Inspect the current target before preparing a new draft.",
      "审阅已过期，请核对当前目标后再准备草稿。",
    ],
    review_expired: [
      "The exact review expired. Inspect the target before preparing another.",
      "确切审阅已过期，请检查目标后再准备一项。",
    ],
    review_required: [
      "Open the linked application draft and review the exact change.",
      "请打开关联应用草稿，审阅确切修改。",
    ],
    input_required: [
      "Answer the recorded question to continue within the existing scope.",
      "请回答记录的问题，以在现有范围内继续。",
    ],
    outputs_verified_quality_unassessed: [
      "The required files were read back and structural checks passed. Their claims and usefulness have not been semantically reviewed.",
      "必需文件已读回并通过结构检查，其结论与实用性尚未经过语义审阅。",
    ],
    required_evidence_unmet: [
      "Some selected evidence or required sections are missing. Inspect the coverage below.",
      "部分所选证据或必需章节缺失，请检查下方覆盖范围。",
    ],
    required_change_unmet: [
      "A required application change was not verified. The report alone does not complete that outcome.",
      "必需应用修改尚未核验，仅有报告不代表该结果完成。",
    ],
    selected_evidence_unread: [
      "Selected evidence was not read.",
      "所选证据尚未读取。",
    ],
    source_partial_coverage: [
      "Only part of this source was read.",
      "仅阅读了此来源的一部分。",
    ],
    required_section_missing: [
      "A required report section is missing.",
      "缺少必需报告章节。",
    ],
    model_budget_exceeded: [
      "The model-call budget was reached. Inspect existing results before starting other work.",
      "已达到模型调用额度，请先检查已有结果再开始其他工作。",
    ],
    read_budget_exceeded: [
      "The read budget was reached. Existing evidence remains inspectable.",
      "已达到读取额度，仍可检查已有证据。",
    ],
    context_changed: [
      "Privacy or source-sharing permission changed. Review the current scope before continuing.",
      "隐私或来源共享许可已变化，请核对当前范围后再继续。",
    ],
    session_expired: [
      "The original owner session expired. Sign in and explicitly review continuation.",
      "原本人会话已过期，请登录并明确审阅后再继续。",
    ],
    paused: [
      "No new work is dispatched while paused.",
      "暂停期间不会派发新工作。",
    ],
    cancelled_no_rollback: [
      "Future work was cancelled. Stored outputs and completed changes remain.",
      "后续工作已取消，已保存产物和已完成修改仍会保留。",
    ],
    deadline_exceeded: [
      "The run deadline was reached.",
      "已达到此次运行的截止时间。",
    ],
    source_line_exceeds_read_budget: [
      "A source line exceeds the model's 1,800-byte whole-line excerpt budget. Use local compilation or split long lines and upload a new source.",
      "来源单行超过模型1800字节的整行摘录额度。请使用本地整理，或拆分长行后上传新来源。",
    ],
    scope_changed: [
      "Source versions or permissions changed. Refresh and review the scope again.",
      "来源版本或权限已变化，请刷新并重新审阅范围。",
    ],
  };
  const normalized = code.toLowerCase().replace(/^(agent_run_|run_)/, "");
  return labels[normalized]
    ? t(...labels[normalized])
    : t(
        "This run needs attention. Inspect its activity and linked reviews.",
        "此次运行需要处理，请检查活动与关联审阅。",
      );
}
export function agentError(error: unknown, t: Translate) {
  const messages: Record<string, [string, string]> = {
    AGENT_SCOPE_CHANGED: [
      "Sources or provider permissions changed. Refresh and review the scope again.",
      "来源或提供商权限已变化，请刷新并重新审阅范围。",
    ],
    AGENT_RUN_LIMIT: [
      "The retained-run limit has been reached. Ask the operator to review retention.",
      "已达到运行记录保留上限，请操作人员检查保留策略。",
    ],
    SOURCE_LIMIT: [
      "Source storage is full. No file was silently removed.",
      "来源存储已满，没有自动删除文件。",
    ],
    SOURCE_TOO_LARGE: [
      "Choose a UTF-8 source no larger than 1 MiB.",
      "请选择不超过1 MiB的UTF-8来源文件。",
    ],
    SOURCE_FORMAT_INVALID: [
      "Only UTF-8 TXT, Markdown, CSV and JSON sources are supported.",
      "仅支持UTF-8的TXT、Markdown、CSV和JSON文件。",
    ],
    PRIVATE_CONTEXT_HIDDEN: [
      "Private content is hidden. Review visibility before continuing.",
      "私人内容已隐藏，请核对可见性后再继续。",
    ],
    AGENT_UI_SCOPE_CHANGED: [
      "The view changed while loading. Open the current record again.",
      "加载期间界面范围已变化，请重新打开当前记录。",
    ],
    ARTIFACT_VERIFICATION_FAILED: [
      "The downloaded bytes did not match the recorded file. No download was released; inspect the server result.",
      "下载字节与记录文件不符，未提供下载，请检查服务端结果。",
    ],
    RUN_SCOPE_CHANGED: [
      "Source versions or permissions changed. Refresh and review the selected scope again.",
      "来源版本或权限已变化，请刷新并重新审阅所选范围。",
    ],
    RUN_EXPLICIT_MODEL_RETRY_REQUIRED: [
      "This uncertain model call needs a separate explicit retry review.",
      "此结果不确定的模型调用需要单独明确审阅重试。",
    ],
    RUN_STEER_NOT_AVAILABLE: [
      "This run cannot be revised again. Inspect its saved outputs before creating another scoped run.",
      "此运行不能再次修订，请先检查保存输出，再创建其他限定范围的运行。",
    ],
    RUN_LIMIT_REACHED: [
      "The server has reached 100 retained runs. No history was silently removed.",
      "服务端已达到100项运行保留上限，没有自动删除历史。",
    ],
    RUN_SOURCE_SHARING_NOT_APPROVED: [
      "Explicit source-sharing permission is missing for this provider.",
      "尚未明确授权向此提供商共享来源。",
    ],
    RUN_RESUME_NOT_AVAILABLE: [
      "This run cannot resume from its current state. Refresh its progress.",
      "当前状态不能恢复运行，请刷新进展。",
    ],
    RUN_ANSWER_NOT_EXPECTED: [
      "The question is no longer current or its answer limit was reached. Refresh before answering.",
      "问题已不是当前版本，或已达到回答次数上限，请刷新后再回答。",
    ],
    RUN_SESSION_EXPIRED: [
      "The owner session expired. Sign in again and inspect current work.",
      "本人会话已过期，请重新登录并检查当前工作。",
    ],
    SOURCE_SIZE_LIMIT: [
      "A source must be nonempty and at most 1 MiB.",
      "来源不能为空且不能超过1 MiB。",
    ],
    SOURCE_UTF8_REQUIRED: [
      "Save the file as UTF-8 before uploading.",
      "请将文件保存为UTF-8后再上传。",
    ],
    SOURCE_LINE_LIMIT: [
      "A source line is too long. Use lines no larger than 12 KiB.",
      "来源单行过长，每行不能超过12 KiB。",
    ],
    INVALID_SOURCE_TEXT: [
      "The source is empty or contains unsupported null characters.",
      "来源为空或含不支持的空字符。",
    ],
    INVALID_JSON: [
      "The selected JSON is invalid or has duplicate keys.",
      "所选JSON无效或含重复键。",
    ],
    INVALID_CSV: ["The selected CSV is invalid.", "所选CSV无效。"],
    CSV_STRUCTURE_LIMIT: [
      "CSV must have unique headers, consistent rows, up to 40 columns and 10,000 data rows.",
      "CSV需要唯一表头、一致行结构，最多40列和10000行数据。",
    ],
    JSON_STRUCTURE_LIMIT: [
      "This JSON exceeds the supported structure limits.",
      "此JSON超出支持的结构限制。",
    ],
    SOURCE_LINE_EXCEEDS_READ_BUDGET: [
      "A line fits the upload limit but is too long for the model's 1,800-byte whole-line excerpt. Use local compilation or split long source lines, then upload a new source.",
      "单行符合上传限制，但超过模型1800字节的整行摘录额度。请使用本地整理，或将长行拆分后上传新来源。",
    ],
    FILE_CAPACITY_LIMIT: [
      "The source or artifact storage capacity is full. No existing file was silently removed.",
      "来源或产物存储容量已满，没有自动删除已有文件。",
    ],
    FILE_READBACK_UNAVAILABLE: [
      "Stored file bytes cannot currently be read back. Do not assume the upload or output is verified.",
      "暂时无法读回保存字节，请勿认为上传或产物已核验。",
    ],
    FILE_READBACK_MISMATCH: [
      "Stored file bytes differ from their recorded hash. The file is not verified.",
      "保存字节与记录哈希不符，该文件未获核验。",
    ],
    ARTIFACT_RUN_LIMIT: [
      "This run reached its artifact count or byte limit. Inspect the existing files.",
      "此次运行已达到产物数量或字节上限，请检查已有文件。",
    ],
    ARTIFACT_SIZE_LIMIT: [
      "The proposed output exceeds the 256 KiB per-file limit.",
      "拟议输出超过每份文件256 KiB的上限。",
    ],
  };
  return error instanceof ApiError && messages[error.code]
    ? t(...messages[error.code])
    : errorText(error, t);
}
