import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = join(import.meta.dirname, "..");

test("home initiative cue offers view-in-conversation without dismissing", () => {
  const cue = readFileSync(
    join(root, "src/workspace/AliceCheckIn.tsx"),
    "utf8",
  );
  const panel = readFileSync(
    join(root, "src/workspace/AssistantPanel.tsx"),
    "utf8",
  );
  const finding = readFileSync(
    join(root, "src/workspace/InitiativeMessages.tsx"),
    "utf8",
  );
  assert.match(cue, /onOpenConversation\?: \(\) => void/);
  assert.match(cue, /cue\.kind === "initiative"/);
  assert.match(cue, /View in conversation/);
  assert.match(cue, /在对话中查看/);
  assert.match(cue, /Got it/);
  assert.match(panel, /onOpenConversation=\{\(\) => onExpandedChange\?\.\(true\)\}/);
  assert.match(finding, /Proactive suggestion/);
  assert.match(finding, /Sources/);
  assert.equal(cue.includes("Follow up on this"), false);
  assert.equal(cue.includes("/snoozes"), false);
});
