import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("Inbox morning and evening check-ins offer View today / View tasks", () => {
  const inbox = readFileSync(join(root, "src/workspace/NoticeInbox.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(inbox, /View today/);
  assert.match(inbox, /查看今天/);
  assert.match(inbox, /View tasks/);
  assert.match(inbox, /morning_brief/);
  assert.match(inbox, /evening_check/);
  assert.match(inbox, /onReview\("today"\)/);
  assert.match(inbox, /onReview\("tasks"\)/);
  assert.match(app, /"today" \| "assistant" \| "memory" \| "tasks"/);
  assert.equal(inbox.includes("Follow up on this"), false);
  assert.equal(inbox.includes("/snoozes"), false);
});
