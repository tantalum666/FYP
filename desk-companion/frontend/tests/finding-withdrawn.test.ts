import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("withdrawn findings show Sources changed and Got it clears them", () => {
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  assert.match(finding, /withdrawn/);
  assert.match(finding, /Sources changed/);
  assert.match(finding, /依据已变更/);
  assert.match(finding, /Withdrawn suggestion/);
  assert.match(finding, /Proactive suggestion/);
  assert.match(finding, /Got it/);
  assert.equal(finding.includes("Follow up on this"), false);
  assert.equal(finding.includes("/snoozes"), false);
  assert.equal(finding.includes("Open task:"), false);
});
