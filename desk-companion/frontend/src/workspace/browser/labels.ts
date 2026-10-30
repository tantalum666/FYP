import type { Translate } from "../../types";
import type { BrowserJobState } from "./types";

export function browserLimit(name: string, t: Translate) {
  const labels: Record<string, [string, string]> = {
    title_chars: ["Title characters", "标题字数"],
    note_chars: ["Note characters", "备注字数"],
    export_bytes: ["Maximum export bytes", "最大导出字节"],
    review_seconds: ["Review validity (seconds)", "核对有效期（秒）"],
    execution_seconds: ["Execution limit (seconds)", "执行时限（秒）"],
  };
  return labels[name] ? t(...labels[name]) : name;
}
export function browserSourceLabel(id: string, fallback: string, t: Translate) {
  if (id === "python_asyncio")
    return t("Python official docs: asyncio", "Python 官方文档：asyncio");
  if (id === "python_pathlib")
    return t("Python official docs: pathlib", "Python 官方文档：pathlib");
  return fallback;
}

export function browserState(state: BrowserJobState, t: Translate) {
  const labels: Record<BrowserJobState, [string, string]> = {
    review: ["Review before editing", "编辑前待核对"],
    queued: ["Approved · waiting for browser", "已批准 · 等待浏览器"],
    running: ["Browser working", "浏览器执行中"],
    verifying: ["Checking exported bytes", "核对导出内容中"],
    succeeded: ["Export completed · inspect evidence", "导出结束 · 请查看证据"],
    failed: ["Workflow stopped with an error", "流程因错误停止"],
    cancelling: ["Stopping · outcome pending", "正在停止 · 结果待确认"],
    cancelled: [
      "Stopped · inspect any existing result",
      "已停止 · 请检查已有结果",
    ],
    expired: ["Approval expired", "批准期限已过"],
    unknown: [
      "Outcome unknown · do not repeat the edit",
      "结果未知 · 不要重复编辑",
    ],
  };
  return labels[state]
    ? t(...labels[state])
    : t("Status not recognized", "未识别的状态");
}
export function browserError(error: unknown, t: Translate) {
  const code =
    error && typeof error === "object" && "code" in error
      ? String(error.code)
      : "";
  const labels: Record<string, [string, string]> = {
    PRIVATE_CONTEXT_HIDDEN: [
      "Private details are hidden. Approval is unavailable.",
      "私人详情已隐藏，无法批准。",
    ],
    OWNER_SIGN_IN_REQUIRED: [
      "Sign in as the owner to use this workflow.",
      "请以拥有者身份登录后使用。",
    ],
    AUTH_REQUIRED: ["Sign in again before continuing.", "请重新登录后继续。"],
    VERSION_CONFLICT: [
      "The job changed. Refresh and review the new version.",
      "作业已变化，请刷新并核对新版本。",
    ],
    CONNECTION_LOST: [
      "The response was lost. The operation may have completed. Refresh the job before deciding what to do.",
      "响应丢失，操作可能已完成。请先刷新作业再决定下一步。",
    ],
    BROWSER_UNAVAILABLE: [
      "The browser runtime is unavailable. No new workflow can start.",
      "浏览器运行环境不可用，无法启动新流程。",
    ],
    BROWSER_NOT_READY: [
      "The browser runtime is not ready. Check its current capability status.",
      "浏览器运行环境尚未就绪，请检查当前能力状态。",
    ],
    BROWSER_DISABLED: [
      "Browser execution is disabled by the operator.",
      "操作人员尚未启用浏览器执行。",
    ],
    BROWSER_EXTRA_REQUIRED: [
      "The optional browser dependency is not installed in this runtime.",
      "此运行环境尚未安装可选浏览器依赖。",
    ],
    BROWSER_EXECUTABLE_REQUIRED: [
      "No admitted browser executable is configured.",
      "尚未配置已准入的浏览器程序。",
    ],
    BROWSER_PLATFORM_UNSUPPORTED: [
      "This runtime platform is not supported by the browser adapter.",
      "浏览器适配器不支持此运行平台。",
    ],
    BROWSER_CLEANUP_UNCONFIRMED: [
      "Previous browser cleanup is unconfirmed. New browser work is blocked.",
      "尚未确认上一次浏览器清理，新的浏览器工作已阻止。",
    ],
    BROWSER_BUSY: [
      "Another browser operation is still active. Check its state before retrying.",
      "另一项浏览器操作仍在进行，请先检查其状态。",
    ],
    BROWSER_REVIEW_EXPIRED: [
      "This review expired or was already handled. Refresh before preparing another operation.",
      "此核对已到期或处理，请先刷新再准备其他操作。",
    ],
    BROWSER_SOURCE_CHANGED: [
      "Source evidence changed. Read it again and review a new exact preview.",
      "来源证据已变化，请重新读取并核对新预览。",
    ],
    BROWSER_SOURCE_UNAVAILABLE: [
      "The source observation is unavailable. Read the selected public source again.",
      "来源观察不可用，请重新读取所选公开来源。",
    ],
    BROWSER_HISTORY_LIMIT: [
      "Browser history reached its admission limit. Existing jobs remain available; new records cannot be created.",
      "浏览器历史已达准入上限。已有作业仍可查看，无法创建新记录。",
    ],
    BROWSER_JOB_NOT_FOUND: [
      "This browser job is no longer available.",
      "此浏览器作业已不存在。",
    ],
    BROWSER_OBSERVATION_STALE: [
      "The source observation is stale. Read the selected source again and prepare a new preview.",
      "来源观察已过时，请重新读取所选来源并准备新预览。",
    ],
    BROWSER_EXPORT_MISMATCH: [
      "The downloaded bytes did not match the recorded export. Nothing was saved by this download.",
      "下载内容与记录的导出不一致，本次下载未保存文件。",
    ],
    BROWSER_VIEW_CHANGED: [
      "The view or owner session changed. The result was not opened.",
      "视图或拥有者会话已变化，未打开结果。",
    ],
  };
  return labels[code]
    ? t(...labels[code])
    : t(
        "The request could not be confirmed. Check the current job and runtime status.",
        "请求未能确认，请检查当前作业与运行环境状态。",
      );
}
