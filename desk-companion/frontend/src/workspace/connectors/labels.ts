import type { Translate } from "../../types";
import type { ConnectorState } from "./types";

export function connectorState(state: ConnectorState, t: Translate) {
  const labels: Record<ConnectorState, [string, string]> = {
    review: ["Awaiting exact approval", "等待逐项批准"],
    queued: ["Approved · queued", "已批准 · 等待执行"],
    preflight: ["Checking the approved tool", "正在核对已批准工具"],
    dispatching: ["Call sent · awaiting result", "调用已发出 · 等待结果"],
    observed_result: [
      "Result observed · not independently verified",
      "已观察到结果 · 尚未独立核验",
    ],
    unknown_effect: [
      "Outcome unknown · do not repeat the call",
      "结果未知 · 不要重复调用",
    ],
    failed: ["Call reported an error", "调用报告错误"],
    rejected: ["Call rejected before dispatch", "调用在发出前已拒绝"],
    cancelled: ["Cancelled before dispatch", "已在发出前取消"],
    expired: ["Review or execution deadline expired", "审阅或执行期限已过"],
    unrecognized: [
      "Unrecognized status · controls unavailable",
      "未识别的状态 · 无法操作",
    ],
  };
  return t(...(labels[state] ?? labels.unrecognized));
}
export function connectorError(error: unknown, t: Translate) {
  const code =
    error && typeof error === "object" && "code" in error
      ? String(error.code)
      : "";
  if (
    [
      "OWNER_SIGN_IN_REQUIRED",
      "AUTH_REQUIRED",
      "CONNECTOR_SESSION_EXPIRED",
      "CONNECTOR_OWNER_SESSION_CHANGED",
    ].includes(code)
  )
    return t(
      "The owner session changed or expired. Sign in and reopen the current review.",
      "拥有者会话已变化或到期，请登录并重新打开当前审阅。",
    );
  if (["PRIVATE_CONTEXT_HIDDEN", "CONNECTOR_PRIVACY_CHANGED"].includes(code))
    return t(
      "Privacy choices changed. Show private content and review again before approving.",
      "隐私选择已变化，请显示私人内容并重新核对后批准。",
    );
  if (
    [
      "CONNECTOR_VERSION_CONFLICT",
      "CONNECTOR_INTENT_CHANGED",
      "CONNECTOR_GRANT_CHANGED",
      "CONNECTOR_TOOL_CHANGED",
      "CONNECTOR_REVIEW_CLOSED",
      "CONNECTOR_REVIEW_EXPIRED",
    ].includes(code)
  )
    return t(
      "The review or granted tool changed. Refresh and inspect the current exact details.",
      "审阅或已授权工具已变化，请刷新并核对最新完整详情。",
    );
  if (code === "CONNECTION_LOST")
    return t(
      "The response was lost. The request may have reached the server. Refresh saved status before deciding what to do.",
      "响应丢失，请求可能已到达服务端。请先刷新已保存状态再决定下一步。",
    );
  return t(
    "The request could not be confirmed. Refresh the saved status; do not repeat an uncertain external call.",
    "请求尚未确认，请刷新已保存状态；不要重复结果未知的外部调用。",
  );
}
