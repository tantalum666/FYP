import assert from "node:assert/strict";
import test from "node:test";
import {
  consumeChunk,
  emptyStream,
  progressLabel,
  reduceReply,
  readReply,
} from "../src/replyStream.ts";

function frame(event: unknown): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

test("partial frames accumulate the reply and then a done event replaces it", () => {
  let state = emptyStream();
  let buffer = "";
  const first = frame({
    type: "delta",
    text: "Hello, this is a partial",
  }).slice(0, 18);
  const rest =
    frame({ type: "delta", text: "Hello, this is a partial" }).slice(18) +
    frame({ type: "delta", text: " reply." }) +
    frame({
      type: "done",
      reply: {
        mode: "ai",
        kind: "reply",
        message: "Hello, this is a partial reply.",
      },
    });
  ({ state, buffer } = consumeChunk(state, buffer, first));
  assert.equal(state.message, "");
  assert.notEqual(buffer, "");
  ({ state, buffer } = consumeChunk(state, buffer, rest));
  assert.equal(buffer, "");
  assert.equal(state.done, true);
  assert.equal(state.message, "Hello, this is a partial reply.");
  assert.equal(state.reply?.kind, "reply");
});

test("tool progress moves from working to done without keeping arguments", () => {
  const started = reduceReply(emptyStream(), {
    type: "tool",
    phase: "started",
    tool: "owner_clock",
  });
  assert.equal(started.tools.length, 1);
  assert.equal(started.tools[0].phase, "started");
  assert.equal(progressLabel(started.tools[0].phase, "en"), "Working");
  assert.equal(progressLabel(started.tools[0].phase, "zh"), "进行中");
  const finished = reduceReply(started, {
    type: "tool",
    phase: "finished",
    tool: "owner_clock",
    outcome: "ok",
    saved: false,
  });
  assert.equal(finished.tools.length, 1);
  assert.equal(finished.tools[0].phase, "finished");
  assert.equal(finished.tools[0].saved, false);
  assert.equal(progressLabel("finished", "zh"), "完成");
  assert.equal("arguments" in finished.tools[0], false);
});

test("a preview replaces the visible text and a later delta appends", () => {
  const preview = reduceReply(emptyStream(), { type: "preview", text: "Tue" });
  const grown = reduceReply(preview, {
    type: "preview",
    text: "Tuesday morning",
  });
  assert.equal(grown.message, "Tuesday morning");
  const cleared = reduceReply(grown, { type: "preview", text: "" });
  assert.equal(cleared.message, "");
  const fallback = reduceReply(cleared, { type: "delta", text: "Hello" });
  assert.equal(fallback.message, "Hello");
});

test("an error event ends the turn", () => {
  const state = reduceReply(emptyStream(), {
    type: "error",
    code: "OPERATION_ID_REQUIRED",
    status: 422,
  });
  assert.equal(state.done, true);
  assert.equal(state.error, "OPERATION_ID_REQUIRED");
  assert.equal(state.status, 422);
});

test("an EOF after a preview is not a completed operation", async () => {
  const state = await readReply(
    new Response(frame({ type: "preview", text: "Preparing…" })),
    () => {},
  );
  assert.equal(state.message, "Preparing…");
  assert.equal(state.done, false);
  assert.equal(state.reply, null);
});

test("a buffered native reply and an error frame retain distinct terminal states", async () => {
  const reply = {
    message: "Review this draft",
    kind: "draft",
    saved: false,
    conversation_id: "scope",
  };
  const complete = await readReply(
    new Response(frame({ type: "done", reply })),
    () => {},
  );
  assert.equal(complete.done, true);
  assert.deepEqual(complete.reply, reply);
  const failed = await readReply(
    new Response(frame({ type: "error", code: "AUTH_REQUIRED", status: 401 })),
    () => {},
  );
  assert.equal(failed.done, true);
  assert.equal(failed.status, 401);
  assert.equal(failed.reply, null);
});
