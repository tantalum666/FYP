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
    succeeded: ["Results ready", "结果已就绪"],
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
    ? t("Local", "本地")
    : mode === "model"
      ? t("AI", "AI")
      : t("Unknown mode", "未知模式");
}
export function blockLabel(code: string, t: Translate) {
  const labels: Record<string, [string, string]> = {
    application_running: [
      "An application is working. No approval is needed right now.",
      "应用正在处理，目前不需要批准。",
    ],
    application_scope_changed: [
      "The application workspace changed or disconnected. Check the connection before continuing.",
      "应用工作空间已变化或断开，请先核对连接。",
    ],
    application_source_changed: [
      "A selected input file changed. Review its new version in a new work request.",
      "所选资料文件已变化，请在新的工作请求中核对新版本。",
    ],
    application_result_unknown: [
      "Check the existing file result before preparing another change.",
      "请先核验已有文件结果，再准备修改。",
    ],
    application_source_not_selected: [
      "This input file was not selected for the work.",
      "此次工作没有选择这份资料。",
    ],
    application_job_not_selected: [
      "The referenced file belongs to other work.",
      "引用的文件属于其他工作。",
    ],
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
    personal_context_changed: [
      "Selected personal context or its consent changed. Inspect earlier outputs and start new work with an explicit current selection; resuming cannot refresh this grant.",
      "所选个人上下文或其许可已变化。请检查之前的输出，并明确选择当前内容后建立新工作；恢复不能刷新此授权。",
    ],
    personal_context_binding_changed: [
      "The owner session or context binding changed. Start new work with a new explicit context selection.",
      "本人会话或上下文绑定已变化。请重新明确选择上下文后建立新工作。",
    ],
    personal_context_binding_invalid: [
      "The saved personal-context binding cannot be validated. Start new work with a new explicit selection.",
      "无法核验保存的个人上下文绑定。请重新明确选择后建立新工作。",
    ],
    personal_context_unavailable: [
      "Selected personal context is no longer available. A new scoped run is needed.",
      "所选个人上下文已不可用，需要建立新的限定范围运行。",
    ],
    personal_context_not_approved: [
      "Personal-context sharing is not approved for this run. Review settings and make a new explicit selection in new work.",
      "此次运行未获准共享个人上下文。请检查设置，并在新工作中重新明确选择。",
    ],
    personal_context_limit: [
      "The selected personal context exceeds the bounded projection. Choose a smaller selection in new work.",
      "所选个人上下文超过有界投影限制。请在新工作中选择更少内容。",
    ],
    connector_scope_changed: [
      "Configured connector tools or their permissions changed. Inspect existing effects before starting new work with the current tool scope.",
      "已配置连接工具或其权限已变化。请先检查已有操作，再以当前工具范围建立新工作。",
    ],
    connector_sharing_not_approved: [
      "Returning connector responses to the selected model destination is not approved.",
      "尚未批准将连接工具响应返回至所选模型目的地。",
    ],
    tool_budget_exceeded: [
      "The run reached its tool-call allowance. Inspect existing results and unknown effects before starting other work.",
      "此次运行已达到工具调用额度。请先检查已有结果和未知操作，再开始其他工作。",
    ],
    tool_not_allowed: [
      "The requested tool is outside this run's selected permissions.",
      "请求工具超出此次运行选择的权限。",
    ],
    tool_receipt_conflict: [
      "Tool evidence does not match its reserved request. Keep the outcome unresolved and inspect the linked effect.",
      "工具证据与保留请求不匹配。结果仍未解决，请检查关联操作。",
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
  if (
    error instanceof ApiError &&
    (error.code.startsWith("RUN_PERSONAL_CONTEXT_") ||
      [
        "RUN_CONNECTOR_SCOPE_CHANGED",
        "RUN_CONNECTOR_SHARING_NOT_APPROVED",
        "RUN_TOOL_BUDGET_EXCEEDED",
        "RUN_TOOL_NOT_ALLOWED",
        "RUN_TOOL_RECEIPT_CONFLICT",
      ].includes(error.code))
  )
    return blockLabel(error.code, t);
  const messages: Record<string, [string, string]> = {
    VOICE_INPUT_CHANGED: [
      "The input changed before it could be frozen. Select the current snapshot and review it again.",
      "固定前输入已变化，请选择当前快照并重新审阅。",
    ],
    VOICE_INPUT_TOO_LARGE: [
      "This voice input is too large to use as a goal. No truncated text was selected.",
      "此语音输入过长，不能作为目标；未选择截断文字。",
    ],
    VOICE_DRAFT_EXPIRED: [
      "The temporary voice draft expired or was lost after restart. Review a new snapshot; work is not started automatically.",
      "临时语音草稿已到期或因重启丢失。请审阅新快照，不会自动开始工作。",
    ],
    VOICE_DRAFT_RESPONSE_INVALID: [
      "The snapshot response did not match your selection. Keep talking or select and review an input again.",
      "快照响应与选择不符，可继续交谈或重新选择并审阅输入。",
    ],
    VOICE_DRAFT_LIMIT: [
      "The temporary voice draft limit was reached. Wait for earlier drafts to expire.",
      "已达到临时语音草稿数量上限，请等待先前草稿到期。",
    ],
    VOICE_CONTEXT_CHANGED: [
      "Voice privacy, session or provider changed. Review a new snapshot in the current owner session.",
      "语音隐私、会话或提供商已变化，请在当前拥有者会话中重新审阅快照。",
    ],
    VOICE_DRAFT_ALREADY_USED: [
      "This voice snapshot already created work. Inspect the saved run instead of starting it again.",
      "此语音快照已创建工作，请检查保存运行，不要再次开始。",
    ],
    VOICE_STEER_REQUIRES_SNAPSHOT: [
      "Updating current work needs the reviewed voice snapshot.",
      "更新当前工作需要已复核的语音快照。",
    ],
    CONVERSATION_WORK_INTERRUPTED: [
      "The update did not finish. Current work is unchanged. Retry the same update.",
      "更新没有完成。当前工作未改变。请重试同一次更新。",
    ],
    CONVERSATION_WORK_RESULT_UNKNOWN: [
      "The update result was not confirmed. Retry the same update before trying a different goal.",
      "更新结果尚未确认。请先重试同一次更新，再改用其他目标。",
    ],
    OPERATION_ID_CONFLICT: [
      "This update already used a different goal. Review the current work before trying again.",
      "这次更新已经用过另一个目标。请先查看当前工作，再重新尝试。",
    ],

    WORK_SEARCH_CHANGED: [
      "Saved records changed while paging. Submit the search again to refresh from the first page.",
      "翻页时保存记录已变化，请重新提交搜索，从第一页刷新。",
    ],
    WORK_SEARCH_CAPACITY_EXCEEDED: [
      "Saved metadata exceeds the search limit. Ask the operator to inspect retention; partial results are not shown.",
      "保存的元数据超过搜索容量，请操作人员检查保留情况；不会显示不完整结果。",
    ],
    WORK_SEARCH_METADATA_INVALID: [
      "Some saved metadata could not be read safely. Ask the operator to inspect the records; no files were changed.",
      "部分保存元数据无法安全读取，请操作人员检查记录；文件未被更改。",
    ],
    WORK_SEARCH_PRIVACY_CHANGED: [
      "Privacy changed during search. Reopen the current private view before searching again.",
      "搜索期间隐私已变化，请重新打开当前私人界面后再搜索。",
    ],
    WORK_SEARCH_RESPONSE_INVALID: [
      "The result did not match the requested record or page. Submit the search again before opening anything.",
      "返回结果与所请求的记录或页面不符，请重新搜索后再打开。",
    ],
    WORK_SEARCH_QUERY_LIMIT: [
      "Use a search query of at most 200 characters.",
      "搜索内容不能超过200个字符。",
    ],
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

export function workTime(value: string, t: Translate) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()))
    return t("Time unavailable", "时间不可用");
  return new Intl.DateTimeFormat(t("en-GB", "zh-CN"), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
