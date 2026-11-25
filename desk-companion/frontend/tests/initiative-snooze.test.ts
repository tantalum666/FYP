import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("conversation findings offer remind-later without claiming a send", () => {
  const source = fs.readFileSync(
    new URL("../src/workspace/InitiativeMessages.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /Remind me later/);
  assert.match(source, /稍后再提醒/);
  assert.match(source, /\/initiative\/" \+ finding\.id \+ "\/snoozes/);
  assert.match(source, /minutes:\s*60/);
  assert.match(source, /Got it/);
  assert.match(source, /\/dismissals/);
  assert.match(source, /canActOnFinding\(finding\)/);
});
