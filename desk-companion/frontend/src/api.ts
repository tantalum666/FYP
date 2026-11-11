import { readReply, type StreamReply, type StreamState } from "./replyStream";
import { apiFetch, isNative, native } from "./native";
export class ApiError extends Error {
  constructor(
    public code: string,
    public status = 0,
  ) {
    super(code);
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(
    () => controller.abort(),
    [
      "/assistant/messages",
      "/assistant/retained-messages",
      "/browser/observations",
    ].includes(path)
      ? 75000
      : 12000,
  );
  try {
    const response = await apiFetch(path, {
      ...options,
      credentials: "same-origin",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Desk-Request": "1",
        ...options.headers,
      },
    });
    const body = await response.json();
    if (!response.ok) {
      if (
        path !== "/session" &&
        response.status === 401 &&
        body.error?.code === "AUTH_REQUIRED"
      )
        window.dispatchEvent(new Event("desk:auth-required"));
      throw new ApiError(body.error?.code ?? "REQUEST_FAILED", response.status);
    }
    if (
      ["/session", "/session/preview", "/session/connect"].includes(path) &&
      options.method
    )
      window.dispatchEvent(
        new CustomEvent("desk:session", {
          detail: {
            reason: options.method === "DELETE" ? "signed_out" : "connected",
          },
        }),
      );
    return body as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("CONNECTION_LOST");
  } finally {
    clearTimeout(timer);
  }
}

export interface PendingWrite {
  path: string;
  body: unknown;
  key: string;
}
const pendingKey = "desk.pending-write";
let identityGeneration = 0;
export function pendingWrite(): PendingWrite | null {
  try {
    return JSON.parse(sessionStorage.getItem(pendingKey) ?? "null");
  } catch {
    return null;
  }
}
export async function write<T>(path: string, body: unknown): Promise<T> {
  const existing = pendingWrite();
  if (
    existing &&
    (existing.path !== path ||
      JSON.stringify(existing.body) !== JSON.stringify(body))
  ) {
    throw new ApiError("PENDING_WRITE");
  }
  const operation = existing ?? { path, body, key: crypto.randomUUID() };
  sessionStorage.setItem(pendingKey, JSON.stringify(operation));
  try {
    const response = await request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "X-Operation-Id": operation.key },
    });
    clearPending(operation.key);
    return response;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      error.status !== 401 &&
      error.status !== 408
    )
      clearPending(operation.key);
    throw error;
  }
}
function aborted(signal: AbortSignal): Promise<never> {
  return new Promise((_, reject) => {
    const fail = () =>
      reject(new DOMException("The operation was aborted.", "AbortError"));
    if (signal.aborted) fail();
    else signal.addEventListener("abort", fail, { once: true });
  });
}

export async function writeStream(
  path: string,
  body: unknown,
  onState: (state: StreamState) => void,
): Promise<StreamReply> {
  const existing = pendingWrite();
  if (
    existing &&
    (existing.path !== path ||
      JSON.stringify(existing.body) !== JSON.stringify(body))
  ) {
    throw new ApiError("PENDING_WRITE");
  }
  const operation = existing ?? { path, body, key: crypto.randomUUID() };
  sessionStorage.setItem(pendingKey, JSON.stringify(operation));
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 75000);
  try {
    const response = await Promise.race([
      apiFetch(path, {
        method: "POST",
        credentials: "same-origin",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-Desk-Request": "1",
          "X-Operation-Id": operation.key,
        },
        body: JSON.stringify(body),
      }),
      aborted(controller.signal),
    ]);
    if (!response.ok) {
      let code = "REQUEST_FAILED";
      try {
        const payload = await response.json();
        code = payload.error?.code ?? code;
      } catch {
        /* The status is enough when the body is not JSON. */
      }
      if (response.status === 401 && code === "AUTH_REQUIRED")
        window.dispatchEvent(new Event("desk:auth-required"));
      throw new ApiError(code, response.status);
    }
    const state = await Promise.race([
      readReply(response, onState),
      aborted(controller.signal),
    ]);
    if (state.error) throw new ApiError(state.error, state.status ?? 500);
    if (!state.done || !state.reply) throw new ApiError("CONNECTION_LOST");
    clearPending(operation.key);
    return state.reply;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      error.status !== 401 &&
      error.status !== 408
    )
      clearPending(operation.key);
    if (error instanceof ApiError) throw error;
    throw new ApiError("CONNECTION_LOST");
  } finally {
    clearTimeout(timer);
  }
}
export async function retryPending(): Promise<unknown> {
  const op = pendingWrite();
  if (op) {
    const generation = identityGeneration;
    const result =
      op.path === "/assistant/messages/stream"
        ? await writeStream(op.path, op.body, () => {})
        : await write(op.path, op.body);
    if (generation !== identityGeneration) return;
    window.dispatchEvent(
      new CustomEvent("desk:write-recovered", {
        detail: { operation: op, result },
      }),
    );
    return result;
  }
}
export function clearPending(key?: string) {
  if (key === undefined) identityGeneration += 1;
  if (key === undefined || pendingWrite()?.key === key)
    sessionStorage.removeItem(pendingKey);
}

export async function downloadFile(path: string, filename: string) {
  if (!isNative) {
    await request("/session");
    const link = document.createElement("a");
    link.href = "/api" + path;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }
  const response = await apiFetch(path, { headers: { "X-Desk-Request": "1" } });
  if (!response.ok) {
    const body = await response.json();
    throw new ApiError(body.error?.code ?? "REQUEST_FAILED", response.status);
  }
  if (isNative) {
    const bytes = new Uint8Array(await response.arrayBuffer());
    let raw = "";
    for (const value of bytes) raw += String.fromCharCode(value);
    await native.exportFile({ filename, bodyBase64: btoa(raw) });
    return;
  }
}

export function errorText(
  error: unknown,
  t: (en: string, zh: string) => string,
) {
  const code = error instanceof ApiError ? error.code : "REQUEST_FAILED";
  const messages: Record<string, [string, string]> = {
    APP_SCOPE_REQUIRED: [
      "The app did not receive the required permissions. Reconnect and review the access requested.",
      "此应用未获得必要权限，请重新连接并核对访问范围。",
    ],
    APP_ACCOUNT_UNVERIFIED: [
      "The provider could not verify this account's email address.",
      "服务提供方未能验证此账号的邮箱地址。",
    ],
    APP_RESPONSE_TOO_LARGE: [
      "The result is too large. Select an item or request fewer results.",
      "结果过大，请指定一项内容或减少读取数量。",
    ],

    APP_NOT_CONFIGURED: [
      "This app's connection setup is not finished.",
      "此应用的连接设置尚未完成。",
    ],
    APP_NOT_CONNECTED: [
      "Connect this app in Connections first.",
      "请先在连接页面授权此应用。",
    ],
    APP_RECONNECT_REQUIRED: [
      "Reconnect this app to renew its permission.",
      "请重新连接此应用以更新授权。",
    ],
    APP_PERMISSION_REQUIRED: [
      "This account has not granted the required access. A work or school administrator may need to approve it.",
      "此账号尚未获准访问，工作或学校管理员可能需要批准。",
    ],
    APP_ITEM_UNAVAILABLE: [
      "This item or service is unavailable for the connected account.",
      "此账号无法访问这项内容或服务。",
    ],
    APP_RATE_LIMIT: [
      "The connected app is temporarily limiting requests. Try again later.",
      "此应用暂时限制了请求，请稍后重试。",
    ],
    APP_CONNECTION_FAILED: [
      "The connected app could not be reached.",
      "暂时无法连接此应用。",
    ],
    APP_CONNECTION_CHANGED: [
      "The connected account changed. Read the current account before continuing.",
      "连接的账号已变化，请刷新后继续。",
    ],

    APP_CALLBACK_UNAVAILABLE: [
      "Open Apps from the configured local address to connect this account.",
      "请通过已配置的本机地址打开应用连接页面。",
    ],
    CHAT_DELIVERY_UNCONFIRMED: [
      "Connection lost. Your message and files are kept. Check delivery before sending again.",
      "连接中断，消息和附件已保留。请先核对发送结果。",
    ],
    CHAT_FILE_FORMAT: [
      "Choose a PDF, Office document, UTF-8 text file or PNG/JPEG/WebP image.",
      "请选择 PDF、Office文档、UTF-8文本或 PNG/JPEG/WebP 图片。",
    ],
    CHAT_FILE_SIZE: [
      "Choose a non-empty file up to 2 MB.",
      "请选择非空且不超过2MB的文件。",
    ],
    CHAT_FILE_COUNT: [
      "Up to four files per conversation. Start a new chat to add more.",
      "每段对话最多四个文件，添加更多文件请开始新对话。",
    ],
    CHAT_FILE_CAPACITY: [
      "File space is busy. Start a new chat or try again shortly.",
      "附件空间暂时已满，请开始新对话或稍后重试。",
    ],
    CHAT_FILE_EXPIRED: [
      "This file is no longer available. Choose it again before sending.",
      "这个附件已失效，请重新选择后发送。",
    ],
    CHAT_FILES_CHANGED: [
      "The conversation changed before sending. Your message was not submitted.",
      "发送前对话已变化，这条消息尚未提交。",
    ],
    CHAT_FILES_UNAVAILABLE: [
      "File reading is unavailable on this connection. Your selection is kept.",
      "当前连接暂不支持读取附件，已保留你的选择。",
    ],
    EMAIL_CONNECTION_FAILED: [
      "Could not reach the mail provider. Check the connection and try again.",
      "暂时无法连接邮箱服务，请检查网络后重试。",
    ],
    EMAIL_NOT_CONNECTED: [
      "Connect Gmail or Microsoft 365 in Connections first.",
      "请先在连接页面授权 Gmail 或 Microsoft 365。",
    ],
    EMAIL_CONNECTION_CHANGED: [
      "The sending account changed. Prepare a new email for review.",
      "发件账号已变化，请重新准备邮件。",
    ],
    EMAIL_RECIPIENT_REJECTED: [
      "The mail provider rejected the recipient. Check the address.",
      "邮箱服务拒绝了这个收件地址，请核对。",
    ],
    EMAIL_SEND_REJECTED: [
      "The mail provider rejected this message. It was not accepted for sending.",
      "邮箱服务拒绝了这封邮件，尚未提交发送。",
    ],
    EMAIL_SEND_UNKNOWN: [
      "The mail provider's final receipt was lost. Check Sent mail before sending again; Alice will not resend automatically.",
      "邮件服务的最终回执丢失。请先检查已发送邮件；Alice 不会自动重发。",
    ],
    VOICE_SELECTION_MISMATCH: [
      "The voice service returned a different voice. The call was stopped.",
      "语音服务返回了不同音色，会话已停止。",
    ],
    LOCAL_OWNER_UNAVAILABLE: [
      "Open this workspace on your desk, or connect this device first.",
      "请在桌面打开此工作空间，或先连接本设备。",
    ],
    LINUX_DESKTOP_UNAVAILABLE: [
      "The Linux desktop, editor, browser or accessibility bridge is not ready. Open a desktop session and check the setup.",
      "Linux 桌面、编辑器、浏览器或辅助功能连接尚未就绪。请打开桌面会话并检查配置。",
    ],
    COMPUTER_DISABLED: [
      "Local note execution is disabled on this desk.",
      "本桌面未启用本地笔记执行。",
    ],
    OPENAI_REGION_UNSUPPORTED: [
      "The assistant service is unavailable from this connection.",
      "当前连接暂时无法使用云端助理。",
    ],
    COMPUTER_USE_UNAVAILABLE: [
      "Browser operation is not connected on this desk.",
      "当前桌面尚未接好浏览器操作。",
    ],
    COMPUTER_SITE_UNAVAILABLE: [
      "This website could not be opened. Check the connection or the site's access requirements.",
      "无法打开这个网站，请检查网络或网站的访问要求。",
    ],
    COMPUTER_CLEANUP_REQUIRED: [
      "The previous browser did not confirm closing. Check it before starting again.",
      "上一个浏览器尚未确认关闭，请先检查再开始。",
    ],
    COMPUTER_SOURCE_CHANGED: [
      "The saved browser state changed or is unavailable. Start a new browser task.",
      "保存的浏览器状态已变化或不可用，请重新开始浏览器任务。",
    ],
    COMPUTER_ENVIRONMENT_REVIEW_REQUIRED: [
      "This restored record has no browser session attached. Inspect the saved result first.",
      "恢复的记录未附带浏览器会话，请先检查已有结果。",
    ],
    BROWSER_EXTRA_REQUIRED: [
      "The browser component needs setup on this desk.",
      "当前桌面还需要安装浏览器组件。",
    ],
    BROWSER_EXECUTABLE_REQUIRED: [
      "Choose the browser installed on this desk.",
      "需要指定当前桌面已安装的浏览器。",
    ],
    FOLDER_NOT_CONFIGURED: [
      "Name one real folder before preparing a folder file.",
      "请先指定一个真实文件夹，再准备文件夹文件。",
    ],
    FOLDER_PATH_DENIED: [
      "That folder must be an existing directory outside this desk’s runtime data, and it cannot be a shortcut.",
      "该文件夹必须是已存在的目录，位于本桌面运行数据之外，且不能是快捷方式。",
    ],
    PERMISSION_CHANGED: [
      "Automatic permission changed before this action started. Review a newly prepared action.",
      "操作开始前自动权限已改变，请核对重新准备的操作。",
    ],
    APPLICATION_UNAVAILABLE: [
      "The application workspace is not connected.",
      "应用工作空间尚未连接。",
    ],
    APPLICATION_BRIDGE_FAILED: [
      "The application connection failed. Check the action result before trying another write.",
      "应用连接失败，请先核对这项操作的结果，再决定是否重新写入。",
    ],
    APPLICATION_BRIDGE_TIMEOUT: [
      "The application did not respond in time. Check the action result before trying another write.",
      "应用未及时响应，请先核对这项操作的结果，再决定是否重新写入。",
    ],
    APPLICATION_CONTENT_MISMATCH: [
      "The application result did not match the reviewed changes. It was not published.",
      "应用结果与核对的修改不一致，没有发布。",
    ],
    APPLICATION_SOURCE_CHANGED: [
      "A source changed. Read the current version and prepare the affected step again.",
      "资料已变化，请读取最新版本后重新准备受影响的步骤。",
    ],
    APPLICATION_ARTIFACT_CHANGED: [
      "This file has changed since the referenced revision. Check the latest task result.",
      "文件已不同于引用的版本，请核对事务中的最新结果。",
    ],
    APPLICATION_ARTIFACT_BUSY: [
      "An earlier action for this file still needs a decision or result check.",
      "这个文件的前一项操作仍需决定或核验结果。",
    ],
    APPLICATION_ARTIFACT_MISSING: [
      "This verified file is not available in the connected workspace.",
      "已连接的工作空间中暂时找不到这份已核验文件。",
    ],
    APPLICATION_VERIFICATION_UNAVAILABLE: [
      "The file could not be reopened for checking. Its saved result is still retained.",
      "暂时无法重新打开文件核验，已保存的结果仍会保留。",
    ],
    APPLICATION_SOURCE_NOT_FOUND: [
      "That source is not in the connected input folder.",
      "已连接的资料夹中没有这份资料。",
    ],
    JOB_TASK_CHANGED: [
      "The linked task changed. Prepare a new job using its current details.",
      "关联事务已变化，请根据最新内容准备新作业。",
    ],
    JOB_NOT_REVIEWABLE: [
      "This job has expired or was already handled. Refresh its status.",
      "作业已到期或已处理，请刷新状态。",
    ],
    JOB_NOT_IN_TAKEOVER: [
      "This browser job is not waiting for you to take over.",
      "这个浏览器作业现在不在等待你接手。",
    ],
    COMPUTER_TARGET_EXISTS: [
      "A file already exists at this destination. It was left unchanged.",
      "目标已有文件，原文件保持不变。",
    ],
    COMPUTER_SCOPE_UNAVAILABLE: [
      "The dedicated notes folder is unavailable or has an unsafe link. Ask the operator to check it.",
      "专用笔记目录不可用或含不安全链接，请操作人员检查。",
    ],
    COMPUTER_SCOPE_CHANGED: [
      "The execution destination changed. Prepare and review a new job.",
      "执行目标已变化，请重新准备并核对作业。",
    ],
    JOB_DEADLINE_EXCEEDED: [
      "The job reached its time limit. Check its recorded result before trying again.",
      "作业已达到时限，请先核对记录的结果。",
    ],
    JOB_CANCELLED_BEFORE_DISPATCH: [
      "Cancelled before the file operation began.",
      "已在文件操作开始前取消。",
    ],
    USER_CANCELLED: [
      "Cancellation requested. Existing results are preserved.",
      "已请求取消，已产生的结果仍保留。",
    ],
    EXECUTOR_RESULT_UNKNOWN: [
      "The executor lost its receipt. Check the existing result; do not repeat the write.",
      "执行回执丢失，请核验已有结果，不要重复写入。",
    ],
    JOB_VERIFICATION_FAILED: [
      "The file could not be verified against the approved text. Review the existing result.",
      "文件未能与批准内容核对一致，请检查已有结果。",
    ],
    PROCESS_RESTARTED: [
      "The desk restarted during execution. Check the existing result.",
      "桌面服务在执行期间重启，请核验已有结果。",
    ],
    SERVICE_STOPPED: [
      "The service stopped during execution. Check the existing result.",
      "服务在执行期间停止，请核验已有结果。",
    ],
    JOB_STILL_RUNNING: [
      "The executor is still responding. Wait for it to stop, then check again.",
      "执行器仍在响应，请等其停止后再次核验。",
    ],
    JOB_LIMIT: [
      "The local job history has reached its limit. New jobs are unavailable; existing jobs and results remain accessible.",
      "本地作业记录已达到上限，暂不能新建作业；已有作业和结果仍可查看。",
    ],
    TASK_NOT_FOUND: ["This task is no longer available.", "此事务已不存在。"],
    TASK_CLOSED: [
      "Reopen this task before making changes.",
      "请先恢复此事务，再进行修改。",
    ],
    TASK_LIMIT: [
      "This workspace supports up to 500 tasks.",
      "此工作空间最多保存500项事务。",
    ],
    TASK_NOTE_REQUIRED: ["Write a progress update first.", "请先填写进展。"],
    CHECK_IN_IN_PAST: [
      "Choose a future check-in, or clear it to use the default interval.",
      "请选择未来检查时间，或清空以使用默认间隔。",
    ],
    PRIVATE_TASK_HIDDEN: [
      "Private task details are hidden in your settings.",
      "设置中已隐藏私人事务详情。",
    ],
    TEXT_AI_UNAVAILABLE: [
      "AI could not respond. Your tasks are safe; retry or use the task form.",
      "AI暂时未能回复，事务数据仍保留；可重试或使用事务表单。",
    ],
    TEXT_AI_NOT_CONFIGURED: [
      "AI text is not configured on this desk.",
      "本设备尚未配置文字AI。",
    ],
    DRAFT_EXPIRED: [
      "This draft expired. Prepare a new one before saving.",
      "草稿已过期，请重新生成后保存。",
    ],
    IMPORT_EXPIRED: [
      "This import preview expired or was applied. Preview the file again.",
      "导入预览已过期或已应用，请重新预览文件。",
    ],
    IMPORT_TOO_LARGE: [
      "Use a smaller file or a shorter date range.",
      "请使用较小文件或缩短日期范围。",
    ],
    IMPORT_RULE_UNSUPPORTED: [
      "This file contains a repeat rule that cannot be safely imported. Export a simpler date range.",
      "文件包含暂不支持的重复规则，请导出较简单的日期范围。",
    ],
    INVALID_ICS: [
      "This calendar file could not be read. Check that it is a valid ICS file.",
      "无法读取此日历文件，请确认它是有效的ICS。",
    ],
    INVALID_BACKUP: [
      "This backup is invalid or has changed. Use an intact Desk Companion backup.",
      "备份格式或校验值不正确，请使用完整的Desk Companion备份。",
    ],
    EVENT_LIMIT: [
      "This prototype supports up to 500 saved event definitions.",
      "此原型最多保存500项主日程。",
    ],
    VOICE_BUSY: [
      "A conversation is already active on another screen or the desk.",
      "桌面或另一终端已有正在进行的会话。",
    ],
    VOICE_NOT_CONFIGURED: [
      "Configure a voice provider on the desk first.",
      "请先在桌面主机配置语音服务。",
    ],
    GOOGLE_NOT_CONFIGURED: [
      "Google connection settings are not configured on this desk.",
      "本设备尚未配置Google连接信息。",
    ],
    GOOGLE_NOT_CONNECTED: [
      "Connect your Google calendar before refreshing.",
      "请先连接Google日历。",
    ],
    GOOGLE_CONNECTION_FAILED: [
      "Google could not be reached. The local calendar is still available.",
      "暂时无法连接Google，本地日历仍可使用。",
    ],
    GOOGLE_RECONNECT_REQUIRED: [
      "Reconnect Google and allow offline calendar access.",
      "请重新连接Google并允许日历离线访问。",
    ],
    GOOGLE_SCOPE_REQUIRED: [
      "Google calendar read permission was not granted. Reconnect to choose it.",
      "尚未取得Google日历读取权限，请重新连接并选择授权。",
    ],
    DEVICE_LIMIT: [
      "Revoke an unused paired screen before adding another.",
      "请先撤销不再使用的配对终端。",
    ],
    SHARE_LIMIT: [
      "Revoke an unused share before creating another.",
      "请先撤销不再使用的分享链接。",
    ],
    OWNER_SIGN_IN_REQUIRED: [
      "Manage access from your main desk.",
      "请在主桌面管理访问权限与重要设置。",
    ],
    PAIRING_EXPIRED: [
      "This pairing request expired or was revoked. Create a new code.",
      "配对申请已过期或撤销，请生成新码。",
    ],
    HARDWARE_NOT_READY: [
      "Connect and verify the output controller first.",
      "请先连接并验证反馈控制器。",
    ],
    HARDWARE_STOPPED: ["Physical outputs are stopped.", "实体反馈已停止。"],
    PRESET_NOT_ALLOWED: [
      "This device action is not supported.",
      "不支持这项设备动作。",
    ],
    ENABLE_MONITORING_FIRST: [
      "Enable observation before starting setup.",
      "开始标定前请先允许观察。",
    ],
    CALIBRATE_REFERENCE_FIRST: [
      "Record your usual position first.",
      "请先记录平时的位置。",
    ],
    INVALID_LOGIN: [
      "The username or password is incorrect.",
      "账号或密码不正确。",
    ],
    AUTH_REQUIRED: ["Reconnect to your workspace.", "请重新连接工作空间。"],
    VERSION_CONFLICT: [
      "This item changed in another window. Close and reopen it to review the latest version.",
      "另一界面已修改此事项。请关闭后重新打开，核对最新版本。",
    ],
    SERIES_HAS_EXCEPTIONS: [
      "This series has individual changes. Edit this occurrence, or keep the original date and repeat rule.",
      "此系列含单次改动。请修改本次，或保留原始日期及重复规则。",
    ],
    VALIDATION_FAILED: [
      "Check the title, dates, timezone and repeat settings. The end must be after the start; clock-change gaps or duplicated times need a different time or UTC.",
      "请检查标题、日期、时区和重复设置。结束须晚于开始；夏令时不存在或重复的时间请改选其他时间或 UTC。",
    ],
    CONVERSATION_WORK_RESULT_INTERRUPTED: [
      "The verified result was not shown. Retry the same update.",
      "已核验结果尚未显示。请重试同一次更新。",
    ],
    CONVERSATION_WORK_RESULT_UNVERIFIED: [
      "That result is not verified, so it is not shown as done.",
      "该结果尚未核验，不会显示为已完成。",
    ],
    CONVERSATION_WORK_RESULT_FAILED: [
      "That result failed, so it is not shown as done.",
      "该结果失败了，不会显示为已完成。",
    ],
    CONNECTION_LOST: [
      "Connection lost. A save may still have completed. Retry the same operation safely.",
      "连接中断，保存可能已完成。可以安全重试同一操作。",
    ],
    PENDING_WRITE: [
      "Resolve the pending save before making another change.",
      "请先处理待确认的保存，再进行其他修改。",
    ],
    REMINDER_NOT_ACTIVE: [
      "This reminder has already been handled or changed.",
      "这条提醒已处理或已更改。",
    ],
    TRY_LATER: [
      "Too many attempts. Please wait a minute.",
      "尝试次数过多，请等一分钟。",
    ],
    EVENT_NOT_FOUND: ["This event is no longer available.", "此事项已不存在。"],
    MEMORY_NOT_FOUND: [
      "That fact is no longer active. Refresh the memory list.",
      "这条事实已不在记忆中，请刷新列表。",
    ],
    MEMORY_LIMIT: [
      "Memory is full. Delete a fact before saving another.",
      "记忆已满，请先删除一条再保存。",
    ],
    MEMORY_DUPLICATE: [
      "That wording is already saved. Correct the existing fact or retire the duplicate.",
      "这条文字已经保存。请更正原事实，或停用重复的一条。",
    ],
    MEMORY_REVIEW_STALE: [
      "Those facts changed. Refresh the list before retiring duplicates.",
      "这些事实已变化。请刷新列表后再停用重复项。",
    ],
    INVALID_EXPIRY: [
      "Choose a timezone-aware expiry time, or clear it.",
      "请选择带时区的到期时间，或清除到期时间。",
    ],
    NARROW_DATE_RANGE: [
      "This view contains too many events. Choose a single day in the date picker or open Today.",
      "当前视图日程过多，请在日期选择器选择一天，或打开今天。",
    ],
  };
  const message = messages[code] ?? [
    "The result could not be confirmed. Please review and retry the same operation.",
    "尚未确认操作结果，请核对并重试同一操作。",
  ];
  return t(...message);
}
