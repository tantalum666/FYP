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
    path === "/assistant/messages" ? 75000 : 12000,
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
    if (!response.ok)
      throw new ApiError(body.error?.code ?? "REQUEST_FAILED", response.status);
    if (path === "/session" && options.method)
      window.dispatchEvent(new Event("desk:session"));
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
    sessionStorage.removeItem(pendingKey);
    return response;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      error.status !== 401 &&
      error.status !== 408
    )
      sessionStorage.removeItem(pendingKey);
    throw error;
  }
}
export async function retryPending(): Promise<unknown> {
  const op = pendingWrite();
  if (op) return write(op.path, op.body);
}
export function clearPending() {
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
      "Sign in as the owner to manage access or sensitive settings.",
      "管理访问或重要设置需要拥有者登录。",
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
    AUTH_REQUIRED: ["Please sign in again.", "请重新登录。"],
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
