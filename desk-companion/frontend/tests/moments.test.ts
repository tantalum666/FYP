import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { momentView, type MomentSnapshot } from "../src/workspace/momentView.ts";

const empty: MomentSnapshot = {
  suggestion: null,
  dismissals: [],
  paused: false,
  pause_reason_en: "",
  pause_reason_zh: "",
};

test("today shows one dismissible suggestion and a separate reset", () => {
  const suggestion = { id: "stretch", reason_en: "Stretch", reason_zh: "活动一下" };
  const shown = momentView({ ...empty, suggestion }, true);
  assert.equal(shown?.suggestion?.id, "stretch");
  assert.equal(shown?.canReset, false);
  assert.equal(shown?.paused, null);

  const remembered = momentView(
    { ...empty, dismissals: [{ id: "stretch" }] },
    true,
  );
  assert.equal(remembered?.suggestion, null);
  assert.equal(remembered?.canReset, true);

  const paused = momentView(
    {
      ...empty,
      paused: true,
      pause_reason_en: "Quiet hours",
      pause_reason_zh: "安静时段",
    },
    true,
  );
  assert.deepEqual(paused?.paused, { en: "Quiet hours", zh: "安静时段" });
  assert.equal(paused?.canReset, false);

  assert.equal(momentView(empty, true), null);
  assert.equal(momentView({ ...empty, suggestion }, false), null);
  assert.equal(momentView(null, true), null);
});

test("the today page mounts that suggestion once", () => {
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const today = fs.readFileSync(
    new URL("../src/components/TodayView.tsx", import.meta.url),
    "utf8",
  );
  const card = fs.readFileSync(
    new URL("../src/workspace/MomentCard.tsx", import.meta.url),
    "utf8",
  );
  assert.equal(app.includes("<MomentCard"), false);
  assert.match(app, /page === "today" && \([\s\S]*?<TodayView/);
  assert.equal(today.match(/<MomentCard\b/g)?.length, 1);
  assert.match(card, /momentView\(/);
  assert.match(card, /"\/moments\/dismissals"/);
  assert.match(card, /"\/moments\/reset"/);
  assert.match(card, /Not now/);
  assert.match(card, /Reset dismissed suggestions/);
});
