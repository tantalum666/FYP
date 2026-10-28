import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("today shows one dismissible suggestion and a reset", () => {
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const card = fs.readFileSync(
    new URL("../src/workspace/MomentCard.tsx", import.meta.url),
    "utf8",
  );
  assert.match(app, /<MomentCard/);
  assert.match(card, /Not now/);
  assert.match(card, /Reset dismissed suggestions/);
  assert.match(card, /pause_reason_en/);
});
