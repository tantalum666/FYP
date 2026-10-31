import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {
  actionsFor,
  knowledgeCopy,
  noteCopy,
  goalLine,
  nudgeLine,
  sourceCopy,
} from "../src/workspace/knowledge.ts";

test("the knowledge screen offers correct and forget, and explains a nudge", () => {
  assert.deepEqual(actionsFor("active", null), [
    "correct",
    "forget",
    "expire_week",
  ]);
  assert.deepEqual(actionsFor("active", "2099-01-01T00:00:00Z"), [
    "correct",
    "forget",
    "clear_expiry",
  ]);
  assert.deepEqual(actionsFor("expired", "2020-01-01T00:00:00Z"), ["forget"]);
  assert.equal(knowledgeCopy.title[0], "Saved memories");
  assert.equal(knowledgeCopy.nudgeTitle[0], "Why did you nudge me");
  assert.equal(knowledgeCopy.goalsTitle[0], "Goals you stated");
  assert.equal(
    goalLine({
      title: "finish the report",
      due_at: "2026-10-30T10:00:00+00:00",
      state: "open",
    }).open,
    true,
  );
  assert.equal(
    goalLine({ title: "finish the report", due_at: null, state: "closed" })
      .open,
    false,
  );
  assert.match(knowledgeCopy.forgot[0], /provider's own logs/);
  assert.deepEqual(sourceCopy("owner"), ["Saved by you", "由你保存"]);
  assert.equal(noteCopy("preference")?.[0], "You stated a preference.");
  const line = nudgeLine({
    id: "morning_brief-2026-10-02",
    state: "open",
    reason_en: "Morning briefing fired because it is enabled.",
    reason_zh: "早晨简报已触发。",
    summary_en: "1 open task(s) still followed up, 0 waiting.",
    summary_zh: "仍在跟进的未完成事务 1 件。",
  });
  assert.equal(line.canDismiss, true);
  assert.match(line.reasonEn, /Morning briefing/);
  assert.equal(
    nudgeLine({
      id: line.id,
      state: "dismissed",
      reason_en: line.reasonEn,
      reason_zh: line.reasonZh,
      summary_en: line.summaryEn,
      summary_zh: line.summaryZh,
    }).canDismiss,
    false,
  );
});

test("the memory page is the knowledge screen and extras no longer repeats nudge history", () => {
  const memory = fs.readFileSync(
    new URL("../src/workspace/MemoryPanel.tsx", import.meta.url),
    "utf8",
  );
  const checks = fs.readFileSync(
    new URL("../src/workspace/CheckIns.tsx", import.meta.url),
    "utf8",
  );
  const extras = fs.readFileSync(
    new URL("../src/workspace/ExtrasPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(memory, /actionsFor\(/);
  assert.match(memory, /knowledgeCopy\.title/);
  assert.match(memory, /<CheckIns/);
  assert.match(memory, /<GoalList/);
  assert.match(memory, /<AliasList/);
  assert.match(memory, /<ProfileSummary/);
  assert.match(memory, /<DigestPanel/);
  assert.equal(knowledgeCopy.profileTitle[0], "Profile used in replies");
  assert.match(checks, /knowledgeCopy\.nudgeTitle/);
  assert.doesNotMatch(extras, /<CheckIns/);
  assert.match(extras, /How I should talk and interrupt/);
  assert.match(extras, /form\.tone/);
  assert.match(extras, /form\.verbosity/);
  assert.match(extras, /form\.proactivity/);
  assert.match(extras, /Chat does not change these/);
  assert.match(extras, /Web Push stays off until DESK_WEB_PUSH=1/);
});
