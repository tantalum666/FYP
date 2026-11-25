import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("finding Sources can open a cited task without follow-up or dismiss", () => {
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(finding, /taskIdFromSource/);
  assert.match(finding, /Open task:/);
  assert.match(finding, /打开待办：/);
  assert.match(finding, /onOpenTask\?: \(taskId: string\) => void/);
  assert.match(finding, /Proactive suggestion/);
  assert.match(finding, /Got it/);
  assert.equal(finding.includes("Follow up on this"), false);
  assert.equal(finding.includes("/snoozes"), false);
  assert.match(app, /onOpenTask=\{\(id\) => goPage\("tasks", id\)\}/);
});
