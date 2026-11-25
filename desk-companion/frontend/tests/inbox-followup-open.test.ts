import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("Inbox follow-up receipts offer Open task for the cited task", () => {
  const inbox = readFileSync(join(root, "src/workspace/NoticeInbox.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(inbox, /Open task/);
  assert.match(inbox, /打开待办/);
  assert.match(inbox, /task_id/);
  assert.match(inbox, /kind === "followup"/);
  assert.match(inbox, /onReview\("tasks"/);
  assert.match(app, /goPage\(target, taskId\)/);
  assert.equal(inbox.includes('onReview("tasks")'), false);
  assert.equal(inbox.includes("Follow up on this"), false);
  assert.equal(inbox.includes("/snoozes"), false);
});
