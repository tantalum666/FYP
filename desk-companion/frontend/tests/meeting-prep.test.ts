import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("the conversation offers a meeting brief and labels that reply", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/AssistantPanel.tsx", import.meta.url),
    "utf8",
  );
  const css = fs.readFileSync(
    new URL("../src/workspace/assistant-minimal.css", import.meta.url),
    "utf8",
  );
  assert.match(panel, /Prep me for my next meeting/);
  assert.match(panel, /下一场会要准备什么/);
  assert.match(panel, /turn\.kind === "meeting_prep"/);
  assert.match(panel, /assistant-meeting-prep-label/);
  assert.match(css, /\.assistant-meeting-prep-label/);
  assert.doesNotMatch(panel, /meeting_prep[\s\S]{0,180}Allow once/);
});
