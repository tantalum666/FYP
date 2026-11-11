import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("the conversation offers the reply-owed question and labels that reply", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/AssistantPanel.tsx", import.meta.url),
    "utf8",
  );
  const ask = fs.readFileSync(
    new URL("../src/workspace/replyOwedAsk.tsx", import.meta.url),
    "utf8",
  );
  const css = fs.readFileSync(
    new URL("../src/workspace/assistant-minimal.css", import.meta.url),
    "utf8",
  );
  assert.match(panel, /Who do I need to reply to\?/);
  assert.match(panel, /我该回复谁？/);
  assert.match(panel, /\.kind === "reply_owed"/);
  assert.match(panel, /assistant-reply-owed-label/);
  assert.match(ask, /Who do I need to reply to\?/);
  assert.match(ask, /我该回复谁？/);
  assert.match(css, /\.assistant-reply-owed-label/);
  assert.doesNotMatch(panel, /reply_owed[\s\S]{0,180}Allow once/);
});
