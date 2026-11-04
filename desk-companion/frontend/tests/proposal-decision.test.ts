import assert from "node:assert/strict";
import test from "node:test";
import { proposalDecisionNotice } from "../src/workspace/proposalDecision.ts";

const en = (english: string, _chinese: string) => english;
const zh = (_english: string, chinese: string) => chinese;

for (const kind of ["mailbox_reply", "shopping_advice", "calendar_advice"]) {
  test(`${kind} confirmation reports a task note rather than a calendar or external action`, () => {
    const notice = proposalDecisionNotice({ kind }, "confirm", kind, en);
    assert.match(notice, /task/);
    assert.doesNotMatch(notice, /calendar|sent|paid|purchased|accepted/i);
    assert.match(proposalDecisionNotice({}, "confirm", kind, zh), /事务/);
  });
}
test("a cancelled draft never reports a saved effect", () => {
  assert.equal(
    proposalDecisionNotice({ kind: "mailbox_reply" }, "cancel", undefined, en),
    "Draft cancelled.",
  );
});
test("unknown future proposal kinds do not claim a calendar write", () => {
  assert.doesNotMatch(
    proposalDecisionNotice({ kind: "future_advice" }, "confirm", undefined, en),
    /calendar/i,
  );
  assert.match(
    proposalDecisionNotice({ kind: "change" }, "confirm", undefined, en),
    /calendar/i,
  );
});
