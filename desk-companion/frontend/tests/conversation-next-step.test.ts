import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("the conversation offers the next-step question and labels that reply", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/AssistantPanel.tsx", import.meta.url),
    "utf8",
  );
  const css = fs.readFileSync(
    new URL("../src/workspace/assistant-minimal.css", import.meta.url),
    "utf8",
  );
  assert.match(panel, /What should I do next\?/);
  assert.match(panel, /接下来做什么？/);
  assert.match(panel, /turn\.kind === "next_step"/);
  assert.match(panel, /assistant-next-step-label/);
  assert.match(css, /\.assistant-next-step-label/);
  assert.doesNotMatch(panel, /next_step[\s\S]{0,180}Allow once/);
});
