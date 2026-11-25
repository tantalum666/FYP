import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("finding Sources can open a cited memory without follow-up or dismiss", () => {
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  const memory = readFileSync(join(root, "src/workspace/MemoryPanel.tsx"), "utf8");
  const list = readFileSync(join(root, "src/workspace/MemoryFactList.tsx"), "utf8");
  assert.match(finding, /memoryIdFromSource/);
  assert.match(finding, /Open memory:/);
  assert.match(finding, /打开记忆：/);
  assert.match(finding, /onOpenMemory\?: \(memoryId: string\) => void/);
  assert.match(finding, /Proactive suggestion/);
  assert.match(finding, /Got it/);
  assert.equal(finding.includes("Follow up on this"), false);
  assert.equal(finding.includes("/snoozes"), false);
  assert.equal(finding.includes("Open task:"), false);
  assert.match(app, /onOpenMemory=\{\(id\) => goPage\("memory", id\)\}/);
  assert.match(app, /initialFactId=\{memoryToOpen\}/);
  assert.match(memory, /initialFactId/);
  assert.match(list, /data-memory-id/);
});
