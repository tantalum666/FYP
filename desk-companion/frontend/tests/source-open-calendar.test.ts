import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("finding Sources can open a cited local calendar without follow-up or dismiss", () => {
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  const app = readFileSync(join(root, "src/App.tsx"), "utf8");
  assert.match(finding, /localCalendarRef/);
  assert.match(finding, /Open calendar:/);
  assert.match(finding, /打开日程：/);
  assert.match(finding, /onOpenCalendar\?: \(ref: string\) => void/);
  assert.match(finding, /Proactive suggestion/);
  assert.match(finding, /Got it/);
  assert.equal(finding.includes("Follow up on this"), false);
  assert.equal(finding.includes("/snoozes"), false);
  assert.equal(finding.includes("Open task:"), false);
  assert.equal(finding.includes("Open memory:"), false);
  assert.match(app, /onOpenCalendar=\{openCitedCalendar\}/);
  assert.match(app, /calendar:google:/);
  assert.match(app, /occurrence_key/);
  assert.match(app, /setDetail\(match\)/);
});
