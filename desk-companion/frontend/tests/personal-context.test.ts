import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
import {
  canSendText,
  contextChoices,
  conversationSwitch,
  personalContextVisible,
  replyMode,
} from "../src/workspace/personal/types.ts";
import type { ContextSettings } from "../src/workspace/personal/types.ts";

const settings: ContextSettings = {
  version: 4,
  save_text_history: false,
  use_text_history_in_ai: false,
  use_memory_in_ai: false,
  share_business_context: false,
  authorization_current: true,
  approved_destinations: [],
  destinations: [
    {
      id: "text/a",
      kind: "text",
      provider: "Configured A",
      endpoint: "https://example.test/v1",
      configured: true,
    },
    {
      id: "voice/b",
      kind: "voice",
      provider: "Unconfigured B",
      endpoint: "https://voice.example.test",
      configured: false,
    },
  ],
};
test("private text retries preserve one immutable operation ID without browser storage", async () => {
  const previous = ["localStorage", "sessionStorage"].map(
    (key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const,
  );
  for (const key of ["localStorage", "sessionStorage"])
    Object.defineProperty(globalThis, key, {
      configurable: true,
      get() {
        throw new Error("Private text reached browser storage");
      },
    });
  try {
    const attempts: { key: string; serialized: string }[] = [];
    let generated = 0;
    const queue = new PrivateWriteQueue(
      async (op) => {
        attempts.push({ ...op });
        if (attempts.length === 1) throw { status: 0 };
        return { id: "server-record" };
      },
      () => `operation-${++generated}`,
    );
    const body = { content: "Private 中文 memory", category: "preference" };
    await assert.rejects(queue.send("/assistant/memories", body));
    assert.equal(queue.pending, true);
    body.content = "Later edit must not mutate retry";
    assert.deepEqual(await queue.retry(), { id: "server-record" });
    assert.equal(attempts[0].serialized, attempts[1].serialized);
    assert.match(attempts[1].serialized, /Private 中文 memory/);
    assert.equal(attempts[0].key, attempts[1].key);
    assert.equal(generated, 1);
    assert.equal(queue.pending, false);
  } finally {
    for (const [key, descriptor] of previous) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
  }
});
test("unknown outcomes reject changed requests; definite conflicts allow a new reviewed operation", async () => {
  let count = 0;
  const queue = new PrivateWriteQueue(
    async () => {
      count++;
      throw { status: count === 1 ? 408 : 409 };
    },
    () => String(count),
  );
  await assert.rejects(queue.send("/assistant/conversations", { title: "A" }));
  await assert.rejects(queue.send("/assistant/conversations", { title: "B" }), {
    code: "PRIVATE_WRITE_PENDING",
  });
  assert.equal(count, 1);
  await assert.rejects(queue.retry());
  assert.equal(queue.pending, false);
});
test("repeated clicks cannot dispatch simultaneous operations", async () => {
  let complete!: (value: unknown) => void;
  let attempts = 0;
  const queue = new PrivateWriteQueue(
    () => {
      attempts++;
      return new Promise((resolve) => {
        complete = resolve;
      });
    },
    () => "one-id",
  );
  const first = queue.send("/assistant/messages", { message: "Hello" });
  await assert.rejects(
    queue.send("/assistant/messages", { message: "Hello" }),
    { code: "PRIVATE_WRITE_BUSY" },
  );
  await assert.rejects(queue.retry(), { code: "PRIVATE_WRITE_BUSY" });
  assert.equal(attempts, 1);
  complete({ message: "Reply" });
  await first;
  assert.equal(queue.pending, false);
});
test("component disposal clears private recovery; a 410 receipt is never retried automatically", async () => {
  const queue = new PrivateWriteQueue(
    async () => {
      throw { status: 401 };
    },
    () => "id",
  );
  await assert.rejects(
    queue.send("/assistant/messages", { message: "Private" }),
  );
  queue.clear();
  assert.equal(queue.pending, false);
  await assert.rejects(queue.retry(), { code: "PRIVATE_WRITE_MISSING" });
  const processed = new PrivateWriteQueue(
    async () => {
      throw { status: 410, code: "ASSISTANT_REPLY_NOT_RETAINED" };
    },
    () => "id",
  );
  await assert.rejects(
    processed.send("/assistant/messages", { message: "Private" }),
  );
  assert.equal(processed.pending, false);
});
test("owner-only personal context fails closed for missing policy, offline and stale snapshots", () => {
  assert.equal(personalContextVisible(true, true, false, false), true);
  for (const [owner, visible, offline, stale] of [
    [false, true, false, false],
    [true, undefined, false, false],
    [true, false, false, false],
    [true, true, true, false],
    [true, true, false, true],
  ] as const)
    assert.equal(personalContextVisible(owner, visible, offline, stale), false);
});
test("saved-thread sends need opt-in; temporary text remains usable without history permission", () => {
  assert.equal(canSendText("Hello", false, null, settings, false), true);
  assert.equal(canSendText("Hello", false, "thread-a", settings, true), false);
  assert.equal(
    canSendText(
      "Hello",
      false,
      "thread-a",
      { ...settings, save_text_history: true },
      true,
    ),
    true,
  );
  assert.equal(
    canSendText(
      "Hello",
      false,
      "thread-a",
      { ...settings, save_text_history: true },
      false,
    ),
    false,
  );
  assert.equal(canSendText("Hello", true, null, settings, true), false);
  assert.equal(canSendText("  ", false, null, settings, true), false);
});
test("retention and provider context are independent; only displayed configured destinations are approved", () => {
  const retained = contextChoices({ ...settings, save_text_history: true });
  assert.equal(retained.use_memory_in_ai, false);
  assert.equal(retained.share_business_context, false);
  assert.deepEqual(
    contextChoices({ ...settings, share_business_context: true })
      .approved_destinations,
    ["text/a"],
  );
  assert.equal(retained.use_text_history_in_ai, false);
  assert.deepEqual(retained.approved_destinations, []);
  const provider = contextChoices({ ...settings, use_memory_in_ai: true });
  assert.equal(provider.save_text_history, false);
  assert.deepEqual(provider.approved_destinations, ["text/a"]);
  assert.equal(provider.expected_version, 4);
  assert.deepEqual(
    settings.approved_destinations,
    [],
    "reviewing choices must not mutate the source settings",
  );
});
test("thread navigation preserves unsent drafts and cannot race writes or voice", () => {
  assert.equal(conversationSwitch("a", "b", true, false, false), "confirm");
  assert.equal(conversationSwitch("a", null, true, false, false), "confirm");
  assert.equal(conversationSwitch("a", "a", true, false, false), "stay");
  assert.equal(conversationSwitch("a", "b", false, true, false), "stay");
  assert.equal(conversationSwitch("a", "b", false, false, true), "stay");
  assert.equal(conversationSwitch("a", "b", false, false, false), "switch");
});
test("reply labels use recorded mode, never configured-provider availability as proof", () => {
  assert.equal(replyMode("local_rules"), "local");
  assert.equal(replyMode("local"), "local");
  assert.equal(replyMode("ai"), "ai");
  assert.equal(replyMode("cloud"), "ai");
  assert.equal(replyMode("future-mode"), "unknown");
  assert.equal(replyMode(), "unknown");
});
test("assistant and personal-context writes cannot route through the persistent write helper", () => {
  const assistant = readFileSync(
    new URL("../src/workspace/AssistantPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(assistant, /\bwrite\s*[<(]/);
  assert.match(assistant, /mutation\.run<Reply>/);
  const hook = readFileSync(
    new URL("../src/workspace/personal/usePrivateMutation.ts", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(hook, /sessionStorage|localStorage/);
  assert.match(hook, /PrivateWriteQueue/);
  assert.doesNotMatch(
    assistant,
    /transcript.*mutation\.run|mutation\.run.*transcript/,
  );
});

test("a response fence rejects owner results after downgrade, hide/show or reauthentication", async () => {
  const { ResponseFence } =
    await import("../src/workspace/personal/responseFence.ts");
  const fence = new ResponseFence();
  fence.update("owner:one:session1", true);
  const ownerTurn = fence.capture();
  assert.equal(fence.accepts(ownerTurn), true);
  fence.update("display:paired:session1", true);
  assert.equal(
    fence.accepts(ownerTurn),
    false,
    "visibility alone must not permit an old owner reply",
  );
  fence.update("owner:one:session1", true);
  const beforeHide = fence.capture();
  fence.update("owner:one:session1", false);
  fence.update("owner:one:session1", true);
  assert.equal(
    fence.accepts(beforeHide),
    false,
    "hide then show cannot revive an in-flight private reply",
  );
  const beforeLogin = fence.capture();
  fence.update("owner:one:session2", true);
  assert.equal(fence.accepts(beforeLogin), false);
  assert.equal(fence.accepts(fence.capture()), true);
});
