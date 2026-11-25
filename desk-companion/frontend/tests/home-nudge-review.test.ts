import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("home morning and evening check-ins offer View today / View tasks", () => {
  const cue = readFileSync(join(root, "src/workspace/AliceCheckIn.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(cue, /View today/);
  assert.match(cue, /查看今天/);
  assert.match(cue, /View tasks/);
  assert.match(cue, /morning_brief/);
  assert.match(cue, /evening_check/);
  assert.match(cue, /onReviewSurface/);
  assert.match(cue, /Got it/);
  assert.match(app, /onReviewSurface=\{/);
  assert.match(app, /goPage\(target\)/);
  assert.equal(cue.includes("View in conversation"), false);
  assert.equal(cue.includes("/snoozes"), false);
  assert.equal(cue.includes("Follow up on this"), false);
});
