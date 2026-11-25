import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("home task cue offers Open task without replacing Done actions", () => {
  const cue = readFileSync(join(root, "src/workspace/AliceCheckIn.tsx"), "utf8");
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(cue, /Open task/);
  assert.match(cue, /打开待办/);
  assert.match(cue, /onOpenTask/);
  assert.match(cue, /cue\.kind === "task"/);
  assert.match(cue, /Done/);
  assert.match(cue, /Still working/);
  assert.match(cue, /In an hour/);
  assert.match(app, /onOpenTask=\{/);
  assert.match(app, /goPage\("tasks", id\)/);
  assert.equal(cue.includes("View today"), false);
  assert.equal(cue.includes("View in conversation"), false);
  assert.equal(cue.includes("/snoozes"), false);
});
