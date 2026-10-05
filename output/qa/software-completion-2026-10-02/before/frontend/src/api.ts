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
  const timer = window.setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch("/api" + path, {
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

export function errorText(
  error: unknown,
  t: (en: string, zh: string) => string,
) {
  const code = error instanceof ApiError ? error.code : "REQUEST_FAILED";
  const messages: Record<string, [string, string]> = {
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
