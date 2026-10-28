import type { Translate } from "../types";

export interface ToolCall {
  id: number;
  at: string;
  channel: string;
  tool: string;
  risk: string;
  arguments: Record<string, unknown>;
  outcome: string;
  saved: boolean;
  ref_kind: string | null;
  ref_id: string | null;
  message?: string;
}

const OUTCOMES: Record<string, [string, string]> = {
  TOOL_NOT_ALLOWED: [
    "That action is outside the tools this assistant can use. Nothing was changed.",
    "这个动作不在助理可用的工具里，没有做任何修改。",
  ],
  OWNER_SIGN_IN_REQUIRED: [
    "That action is outside the tools this assistant can use. Nothing was changed.",
    "这个动作不在助理可用的工具里，没有做任何修改。",
  ],
  TOOL_ARGUMENTS_INVALID: [
    "I could not prepare that action. Nothing was saved.",
    "没能准备这个动作，没有保存任何内容。",
  ],
  PRESET_NOT_ALLOWED: [
    "I could not prepare that action. Nothing was saved.",
    "没能准备这个动作，没有保存任何内容。",
  ],
  TOOL_TIMEOUT: [
    "That action took too long and was stopped. Nothing further was saved.",
    "这个动作超时并已停止，没有继续保存。",
  ],
  TOOL_FAILED: [
    "That action failed. Nothing was saved.",
    "这个动作失败了，没有保存任何内容。",
  ],
  TOOL_CANCELLED: [
    "That action was cancelled. Nothing was saved.",
    "这个动作已取消，没有保存任何内容。",
  ],
  TOOL_CALL_CONFLICT: [
    "Too many tool calls are in progress. Nothing was changed.",
    "工具调用太多，没有做任何修改。",
  ],
  TOOL_LIMIT_REACHED: [
    "Too many tool calls are in progress. Nothing was changed.",
    "工具调用太多，没有做任何修改。",
  ],
  TOOLS_BUSY: [
    "Too many tool calls are in progress. Nothing was changed.",
    "工具调用太多，没有做任何修改。",
  ],
};

export function riskLabel(risk: string, t: Translate) {
  if (risk === "read") return t("Read", "读取");
  if (risk === "draft") return t("Needs approval", "待批准");
  if (risk === "cancel") return t("Cancel", "取消");
  if (risk === "stop") return t("Stop", "停止");
  return t("Refused", "已拒绝");
}

export function sentenceFor(call: ToolCall, t: Translate) {
  const known = OUTCOMES[call.outcome];
  if (known) return t(known[0], known[1]);
  if (
    call.outcome === "ok" &&
    !call.saved &&
    (call.ref_kind === "proposal" || call.ref_kind === "job")
  ) {
    return t("Prepared for review. Nothing was saved.", "已准备待审，没有保存。");
  }
  if (call.outcome !== "ok" && call.message) return call.message;
  if (call.outcome === "ok" && call.message && planSteps(call).length > 0) return call.message;
  return "";
}

export function planSteps(call: ToolCall): string[] {
  const raw = call.arguments.steps;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((step) => {
      if (typeof step === "string") return step;
      if (step && typeof step === "object" && "text" in step) {
        const text = (step as { text?: unknown }).text;
        return typeof text === "string" ? text : "";
      }
      return "";
    })
    .filter((step) => step.length > 0);
}

export type ActivityState =
  | { kind: "hidden" }
  | { kind: "empty" }
  | {
      kind: "list";
      rows: { call: ToolCall; risk: string; sentence: string; steps: string[] }[];
    };

export function activityState(calls: ToolCall[] | null, t: Translate): ActivityState {
  if (!calls) return { kind: "hidden" };
  if (calls.length === 0) return { kind: "empty" };
  return {
    kind: "list",
    rows: calls.map((call) => ({
      call,
      risk: riskLabel(call.risk, t),
      sentence: sentenceFor(call, t),
      steps: planSteps(call),
    })),
  };
}
