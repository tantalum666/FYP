import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

test("the today page mounts one dismissible suggestion card", () => {
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const today = fs.readFileSync(
    new URL("../src/components/TodayView.tsx", import.meta.url),
    "utf8",
  );
  const card = fs.readFileSync(
    new URL("../src/workspace/MomentCard.tsx", import.meta.url),
    "utf8",
  );
  // Workspace redesign mounts the card under Today, not App.
  assert.equal(app.includes("<MomentCard"), false);
  assert.match(app, /page === "today" && \([\s\S]*?<TodayView/);
  assert.equal(today.match(/<MomentCard\b/g)?.length, 1);
  assert.match(card, /Not now/);
  assert.match(card, /Reset dismissed suggestions/);
  assert.match(card, /pause_reason_en/);
});
