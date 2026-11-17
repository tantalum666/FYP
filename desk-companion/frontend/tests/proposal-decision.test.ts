import assert from "node:assert/strict";
import test from "node:test";
import { proposalDecisionNotice } from "../src/workspace/proposalDecision.ts";

const en = (english: string, _chinese: string) => english;
const zh = (_english: string, chinese: string) => chinese;

test("browser approval reports conversation progress without a device or purchase receipt", () => {
  const notice = proposalDecisionNotice(
    { kind: "browser_research", queued: true },
    "confirm",
    undefined,
    en,
  );
  assert.match(notice, /conversation/);
  assert.doesNotMatch(notice, /device|purchased|booked|completed|saved/i);
});

test("recovering an ended browser task does not claim to start it again", () => {
  assert.match(
    proposalDecisionNotice(
      { kind: "browser_research", queued: false },
      "confirm",
      undefined,
      en,
    ),
    /refreshed/,
  );
  assert.equal(
    proposalDecisionNotice(
      { kind: "browser_research", queued: true },
      "cancel",
      undefined,
      en,
    ),
    "Draft cancelled.",
  );
});

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

test("mail follow-up confirmation does not imply an email was sent", () => {
  const notice = proposalDecisionNotice(
    { kind: "mail_followup" },
    "confirm",
    undefined,
    en,
  );
  assert.match(notice, /follow-up.*linked task/);
  assert.doesNotMatch(notice, /sent|sending|delivered|completed/);
});
test("an accepted email receipt reports sending acceptance, never delivery", () => {
  const notice = proposalDecisionNotice(
    { kind: "email_send" },
    "confirm",
    undefined,
    en,
  );
  assert.equal(notice, "Email accepted for sending.");
  assert.doesNotMatch(notice, /delivered|expired|without making changes/);
});
