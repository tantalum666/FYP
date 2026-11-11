import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("the conversation offers tomorrow's openings and shows them under the reply", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/AssistantPanel.tsx", import.meta.url),
    "utf8",
  );
  const types = fs.readFileSync(
    new URL("../src/workspace/assistantTypes.ts", import.meta.url),
    "utf8",
  );
  assert.match(panel, /\["When am I free tomorrow\?", "我明天什么时候有空？"\]/);
  assert.match(panel, /turn\.kind === "open_time"/);
  assert.match(panel, /Open on the saved calendar/);
  assert.match(panel, /openTime\.openings/);
  assert.match(types, /open_time\?:/);
  assert.match(types, /booked: false/);
});
