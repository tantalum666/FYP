import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  checkBody,
  decisionBody,
  runBody,
  scheduleBody,
  scheduleSkipNotice,
  skillOutcomeNotice,
} from "../src/workspace/savedSkillState.ts";

register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { SavedSkillRun } = await import("../src/workspace/SavedSkillRun.tsx");

const en = (english: string, _chinese: string) => english;
const zh = (_english: string, chinese: string) => chinese;

test("an unchecked checklist is not sent, and a blank note is omitted", () => {
  assert.deepEqual(
    checkBody({
      title: "Friday supply check",
      stepsText: "Count the packs",
      namesText: "quantity",
      passed: false,
    }),
    { ok: false, reason: "not_passed" },
  );
  const ready = checkBody({
    title: " Friday supply check ",
    stepsText: "Count the packs\n",
    namesText: "quantity, 数量",
    passed: true,
  });
  assert.equal(ready.ok, true);
  if (ready.ok) {
    assert.equal(ready.body.passed, true);
    assert.deepEqual(ready.body.input_names, ["quantity", "数量"]);
    assert.equal(Object.hasOwn(ready.body, "tool"), false);
  }
  const fill = runBody({ quantity: "2" }, "  ");
  assert.deepEqual(fill, { inputs: { quantity: "2" } });
  assert.equal(Object.hasOwn(fill, "note"), false);
  const noted = runBody({ quantity: "2" }, " shelf ");
  assert.equal(noted.note, "shelf");
  assert.deepEqual(
    decisionBody({ version: 1, input_hash: "abc" }, "approve"),
    { action: "approve", expected_version: 1, input_hash: "abc" },
  );
  const scheduled = scheduleBody({ quantity: "2" }, "  ", {
    frequency: "daily",
    startLocal: "2026-11-11T09:00",
    timezone: " Asia/Hong_Kong ",
  });
  assert.equal(Object.hasOwn(scheduled, "note"), false);
  assert.equal(scheduled.timezone, "Asia/Hong_Kong");
  assert.equal(Object.hasOwn(scheduled, "tool"), false);
  const scheduledNote = scheduleBody({ quantity: "2" }, " shelf ", {
    frequency: "once",
    startLocal: "2026-11-11T09:00",
    timezone: "Asia/Hong_Kong",
  });
  assert.equal(scheduledNote.note, "shelf");
  assert.match(scheduleSkipNotice("skipped_missed", en) ?? "", /already passed/);
  assert.equal(scheduleSkipNotice("prepared", en), null);
});

test("a saved result is an approval on this desk, and a pending run can still be approved", () => {
  const succeeded = skillOutcomeNotice("succeeded", en);
  assert.match(succeeded, /Saved on this desk after your approval/);
  assert.doesNotMatch(succeeded, /sent|booked|purchased|submitted|verified/i);
  assert.match(skillOutcomeNotice("succeeded", zh), /已按你的批准保存在这台桌上/);
  assert.match(skillOutcomeNotice("pending", en), /Waiting for your approval/);
  assert.match(
    skillOutcomeNotice("pending", en, "schedule"),
    /Prepared at the scheduled time/,
  );
  assert.doesNotMatch(skillOutcomeNotice("pending", en, "schedule"), /sent|booked|purchased/i);
  const run = {
    id: "run-1",
    status: "pending",
    version: 1,
    input_hash: "abc",
    inputs: { quantity: "<script>alert(1)</script>" },
    note: null,
    note_provided: false,
    result: null,
  };
  const pending = renderToStaticMarkup(
    createElement(SavedSkillRun, {
      run,
      t: en,
      disabled: false,
      onDecide() {},
    }),
  );
  assert.match(pending, /Approve/);
  assert.match(pending, /&lt;script&gt;/);
  assert.doesNotMatch(pending, /<script>/);
  const done = renderToStaticMarkup(
    createElement(SavedSkillRun, {
      run: { ...run, status: "succeeded", result: { system_verified: false } },
      t: en,
      disabled: false,
      onDecide() {},
    }),
  );
  assert.match(done, /Saved on this desk after your approval/);
  assert.doesNotMatch(done, /Approve/);
  const tasks = fs.readFileSync(
    new URL("../src/workspace/TaskPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(tasks, /<SavedSkillsPanel/);
  const panel = fs.readFileSync(
    new URL("../src/workspace/SavedSkillsPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(panel, /id="saved-skill-schedule"/);
  assert.match(panel, /Quiet hours, proactive off, and a missed time skip it/);
});
