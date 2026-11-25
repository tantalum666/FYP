import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("Inbox memory follow-up receipts offer View memories", () => {
  const inbox = readFileSync(join(root, "src/workspace/NoticeInbox.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(inbox, /memory_followup/);
  assert.match(inbox, /View memories/);
  assert.match(inbox, /查看记忆/);
  assert.match(inbox, /onReview\("memory"\)/);
  assert.match(inbox, /memory_morning/);
  assert.match(app, /onReview=\{reviewNotice\}/);
  assert.equal(inbox.includes("Open task"), false);
  assert.equal(inbox.includes("/snoozes"), false);
  assert.equal(inbox.includes("Follow up on this"), false);
});
