import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("Inbox calendar update receipts offer View calendar", () => {
  const inbox = readFileSync(join(root, "src/workspace/NoticeInbox.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(inbox, /View calendar/);
  assert.match(inbox, /查看日历/);
  assert.match(inbox, /calendar_deadline/);
  assert.match(inbox, /calendar_conflict/);
  assert.match(inbox, /calendar_decision/);
  assert.match(inbox, /calendar_cancelled/);
  assert.match(inbox, /onReview\("calendar"\)/);
  assert.match(app, /"calendar" \| "assistant" \| "memory" \| "tasks"/);
  assert.equal(inbox.includes("Open calendar"), false);
  assert.equal(inbox.includes("/snoozes"), false);
});
