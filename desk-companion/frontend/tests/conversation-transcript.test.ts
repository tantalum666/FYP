import assert from "node:assert/strict";
import test from "node:test";
import {
  appendLiveTranscript,
  asksApprovalStatus,
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


test("Home shows only the approval headline and ordinary answers retain their own text", () => {
  const turn: ConversationTurn = {
    id: 1, role: "assistant", body: "1 item needs your review.\nPrivate draft details",
    approvalSummary: "1 item needs your review.", kind: "approval_status", approvalTask: "task-a",
  };
  assert.equal(latestAssistantReply([turn]), "1 item needs your review.");
  assert.equal(latestAssistantReply([turn, { id: 2, role: "assistant", body: "Hello" }]), "Hello");
  assert.equal(asksApprovalStatus("现在有什么需要我确认？"), true);
  assert.equal(asksApprovalStatus("Show the original flight options"), false);
});

test("an HKD caption replacement changes just Alice's live amount", () => {
  const first = appendLiveTranscript([], "s", { role: "user", text: "港币三千三百八十九元五角九仙", caption_group: 1 });
  const second = appendLiveTranscript(first, "s", { role: "assistant", text: "Kiwi.com 的报价", caption_group: 1 });
  const corrected = appendLiveTranscript(second, "s", {
    role: "assistant", text: "Kiwi.com 的报价为 HK$3,389.59。", caption_group: 1, caption_replace: true,
  });
  assert.equal(corrected.length, 2);
  assert.equal(corrected[0].body, first[0].body);
  assert.equal(corrected[1].body, "Kiwi.com 的报价为 HK$3,389.59。");
});
