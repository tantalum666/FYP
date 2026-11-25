import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("Inbox View in conversation focuses the bound finding Sources", () => {
  const inbox = readFileSync(join(root, "src/workspace/NoticeInbox.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  assert.match(inbox, /View in conversation/);
  assert.match(inbox, /onReview\("assistant", item\.id\)/);
  assert.match(inbox, /noticeId\?: string/);
  assert.match(app, /focusNoticeId/);
  assert.match(app, /setFocusNoticeId\(noticeId\)/);
  assert.match(finding, /data-finding-id/);
  assert.match(finding, /focusNoticeId/);
  assert.match(finding, /findingMatchesNotice/);
  assert.match(finding, /Proactive suggestion/);
  assert.equal(finding.includes("/snoozes"), false);
  assert.equal(finding.includes("Follow up on this"), false);
  assert.equal(finding.includes("Open task:"), false);
});
