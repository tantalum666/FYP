import assert from "node:assert/strict";
import test from "node:test";
import type { Translate } from "../src/types.ts";
import {
  activityState,
  riskLabel,
  sentenceFor,
  type ToolCall,
} from "../src/workspace/toolActivity.ts";

const en: Translate = (text) => text;
const zh: Translate = (_en, text) => text;

function call(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: 1,
    at: "2026-10-27T00:00:00Z",
    channel: "text",
    tool: "shell_exec",
    risk: "refused",
    arguments: { command: "rm" },
    outcome: "TOOL_NOT_ALLOWED",
    saved: false,
    ref_kind: null,
    ref_id: null,
    ...overrides,
  };
}

test("audit panel stays hidden until the owner list loads, then shows empty or rows", () => {
  assert.equal(activityState(null, en).kind, "hidden");
  assert.equal(activityState([], en).kind, "empty");
  const state = activityState(
    [
      call(),
      call({
        id: 2,
        tool: "calendar_create_draft",
        risk: "draft",
        outcome: "ok",
        ref_kind: "proposal",
        ref_id: "draft-1",
        arguments: { event: { title: "Submit" } },
      }),
    ],
    en,
  );
  assert.equal(state.kind, "list");
  if (state.kind !== "list") return;
  assert.equal(state.rows[0].risk, "Refused");
  assert.match(state.rows[0].sentence, /Nothing was changed/);
  assert.equal(state.rows[1].risk, "Needs approval");
  assert.equal(state.rows[1].sentence, "Prepared for review. Nothing was saved.");
  assert.equal(state.rows[1].call.arguments.event && "title" in (state.rows[1].call.arguments.event as object), true);
});

test("a bounded plan is listed in the audit panel without being marked saved", () => {
  const state = activityState(
    [
      call({
        tool: "propose_plan",
        risk: "read",
        outcome: "ok",
        message: "Tomorrow: 1. Review the draft 2. Keep the afternoon open",
        arguments: {
          title: "Tomorrow",
          steps: [{ text: "Review the draft" }, { text: "Keep the afternoon open" }],
        },
      }),
    ],
    en,
  );
  assert.equal(state.kind, "list");
  if (state.kind !== "list") return;
  assert.deepEqual(state.rows[0].steps, ["Review the draft", "Keep the afternoon open"]);
  assert.match(state.rows[0].sentence, /Review the draft/);
  assert.equal(state.rows[0].call.saved, false);
});

test("owner-readable sentences follow the interface language", () => {
  assert.equal(riskLabel("stop", zh), "停止");
  assert.match(sentenceFor(call({ outcome: "TOOL_TIMEOUT", tool: "memory_query", risk: "read" }), zh), /超时/);
  assert.equal(sentenceFor(call({ outcome: "ok", tool: "memory_query", risk: "read" }), en), "");
  assert.equal(
    sentenceFor(call({ outcome: "TASK_NOT_FOUND", message: "Missing task." }), en),
    "Missing task.",
  );
});
