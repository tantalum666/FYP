import assert from "node:assert/strict";
import test from "node:test";
import {
  appendLiveTranscript,
  latestAssistantReply,
  type ConversationTurn,
} from "../src/workspace/conversationTranscript.ts";

test("two spoken questions remain two exchanges and home shows only the newest answer", () => {
  let turns: ConversationTurn[] = [];
  for (const [caption_group, role, text] of [
    [0, "user", "你能说中文吗？"],
    [0, "assistant", "可以啊，我可以说中文。"],
    [1, "user", "帮我查一下明天的会议。"],
    [1, "assistant", "明天是11月9号，没有安排会议。"],
  ] as const)
    turns = appendLiveTranscript(turns, "session", {
      caption_group,
      role,
      text,
    });
  assert.equal(turns.length, 4);
  assert.equal(latestAssistantReply(turns), "明天是11月9号，没有安排会议。");
  assert.equal(turns[1].body, "可以啊，我可以说中文。");
});
test("delayed older speech updates history without replacing the current response", () => {
  let turns: ConversationTurn[] = [];
  for (const [caption_group, role, text] of [
    [0, "user", "Hi"],
    [0, "assistant", "Hello"],
    [1, "user", "Next question"],
    [1, "assistant", "Current reply"],
  ] as const)
    turns = appendLiveTranscript(turns, "s", { caption_group, role, text });
  turns = appendLiveTranscript(turns, "s", {
    caption_group: 0,
    role: "assistant",
    text: " there.",
  });
  assert.equal(turns[1].body, "Hello there.");
  assert.equal(latestAssistantReply(turns), "Current reply");
  turns = appendLiveTranscript(turns, "s", {
    caption_group: 2,
    role: "user",
    text: "New request",
  });
  assert.equal(latestAssistantReply(turns), "");
});
test("spaces, repeated words and distinct sessions are retained", () => {
  let turns: ConversationTurn[] = [];
  for (const text of ["I", " can", " can", " help."])
    turns = appendLiveTranscript(turns, "one", {
      caption_group: 0,
      role: "assistant",
      text,
    });
  turns = appendLiveTranscript(turns, "two", {
    caption_group: 0,
    role: "assistant",
    text: "Hi again",
  });
  assert.deepEqual(
    turns.map((t) => t.body),
    ["I can can help.", "Hi again"],
  );
});
test("retired fragments do not resurrect messages or displace current history", () => {
  let turns: ConversationTurn[] = [];
  for (let i = 0; i < 50; i++)
    turns = appendLiveTranscript(turns, "s", {
      caption_group: i,
      role: "assistant",
      text: String(i),
    });
  assert.equal(turns.length, 40);
  assert.equal(
    appendLiveTranscript(turns, "s", {
      caption_group: 0,
      role: "user",
      text: "late",
    }),
    turns,
  );
  assert.equal(latestAssistantReply(turns), "49");
});
