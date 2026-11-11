import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {
  canSave,
  citableSources,
  claimBody,
  openBody,
  savedLine,
  sourceBody,
  type SourceBrief,
} from "../src/workspace/sourceBriefState.ts";

test("omitted note, locator, and unknown source stay out of the request", () => {
  assert.deepEqual(openBody({ question: "Which ferry?" }), { question: "Which ferry?" });
  assert.equal("note" in openBody({ question: "Which ferry?" }), false);
  assert.deepEqual(openBody({ question: "Which ferry?", note: "weekday" }), {
    question: "Which ferry?",
    note: "weekday",
  });
  const present = sourceBody({ label: "Star", available: true, body: "Departs at 07:10." });
  assert.equal("locator" in present, false);
  assert.equal("gap" in present, false);
  assert.equal(present.body, "Departs at 07:10.");
  const missing = sourceBody({
    label: "Timetable",
    available: false,
    gap: "Page asked for a login",
  });
  assert.equal("body" in missing, false);
  assert.equal(missing.gap, "Page asked for a login");
  const unknown = claimBody({ kind: "unknown", text: "The return time is not here." });
  assert.deepEqual(unknown, { kind: "unknown", text: "The return time is not here." });
  assert.equal("source_id" in unknown, false);
  assert.equal("quote" in unknown, false);
});

test("a missing source cannot be cited and a gap keeps the saved result incomplete", () => {
  const brief = {
    status: "draft",
    claims: [],
    gaps: [{ id: "g", label: "Timetable", gap: "login", locator: null }],
    sources: [
      { id: "a", label: "Star", available: true },
      { id: "b", label: "Timetable", available: false },
    ],
  } as SourceBrief;
  assert.deepEqual(
    citableSources(brief).map((source) => source.id),
    ["a"],
  );
  assert.equal(canSave(brief), true);
  assert.match(savedLine({ ...brief, status: "saved" }, "en"), /still missing/);
  assert.equal(canSave({ ...brief, status: "saved" }), false);
  assert.equal(
    canSave({ ...brief, gaps: [], claims: [], status: "draft" }),
    false,
  );
});

test("the memory page mounts the comparison and the panel omits empty optional fields", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/SourceBriefPanel.tsx", import.meta.url),
    "utf8",
  );
  const memory = fs.readFileSync(
    new URL("../src/workspace/MemoryPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(memory, /<SourceBriefPanel/);
  assert.match(panel, /openBody\(/);
  assert.match(panel, /sourceBody\(/);
  assert.match(panel, /claimBody\(\{ kind: "unknown"/);
  assert.match(panel, /savedLine\(/);
  assert.doesNotMatch(panel, /note: ""/);
});
