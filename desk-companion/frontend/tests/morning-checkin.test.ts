import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  checkInReady,
  morningErrorCopy,
  visibleCitations,
  type MorningCheckInView,
  type MorningDraft,
} from "../src/workspace/morningCheckInFacts.ts";

register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { MorningCheckInCard, MorningDraftCard } = await import(
  "../src/workspace/MorningCheckIn.tsx"
);

const t = (en: string) => en;
const dentist = "The Thursday dentist visit is private";
const lab = "The Friday lab key is private";

test("a morning check-in stays unarmed until it covers several facts", () => {
  assert.equal(checkInReady(1), false);
  assert.equal(checkInReady(2), true);
  assert.deepEqual(
    visibleCitations([
      { body: `  ${dentist}  ` },
      { body: "" },
      { body: lab },
    ]),
    [dentist, lab],
  );
  assert.equal(
    morningErrorCopy("MORNING_CHECKIN_NEEDS_SEVERAL")?.[0].includes("two follow-ups"),
    true,
  );

  const draft: MorningDraft = {
    due_local: "2026-11-11T09:30",
    timezone: "Asia/Hong_Kong",
    citations: [
      { followup_id: "a", memory_id: "m1", body: dentist },
      { followup_id: "b", memory_id: "m2", body: lab },
    ],
    ready: true,
    armed: false,
  };
  const preview = renderToStaticMarkup(
    createElement(MorningDraftCard, {
      draft,
      t,
      busy: false,
      onApprove() {},
      onDiscard() {},
    }),
  );
  assert.match(preview, /Nothing is scheduled until you approve/);
  assert.match(preview, /Approve check-in/);
  assert.match(preview, new RegExp(dentist));
  assert.match(preview, new RegExp(lab));
  assert.doesNotMatch(preview, /Dismiss/);

  const early = renderToStaticMarkup(
    createElement(MorningDraftCard, {
      draft: { ...draft, ready: false, citations: draft.citations.slice(0, 1) },
      t,
      busy: false,
      onApprove() {},
      onDiscard() {},
    }),
  );
  assert.match(early, /fewer than two follow-ups/);
  assert.doesNotMatch(early, /Approve check-in/);
  assert.doesNotMatch(early, new RegExp(lab));
});

test("the check-in card cites active facts and a dismissed one has no second approve", () => {
  const item: MorningCheckInView = {
    id: "check",
    state: "raised",
    version: 2,
    due_local: "2026-11-11T09:30",
    timezone: "Asia/Hong_Kong",
    citations: [
      { followup_id: "a", memory_id: "m1", body: dentist },
      { followup_id: "b", memory_id: "m2", body: lab },
    ],
    left_out: 1,
    armed: true,
    reason_en: "Morning check-in fired because you approved it.",
    reason_zh: "早晨核对现在发出。",
  };
  const raised = renderToStaticMarkup(
    createElement(MorningCheckInCard, {
      item,
      t,
      busy: false,
      onDismiss() {},
    }),
  );
  assert.match(raised, new RegExp(dentist));
  assert.match(raised, new RegExp(lab));
  assert.match(raised, /Dismiss/);
  assert.doesNotMatch(raised, /Approve check-in/);
  assert.doesNotMatch(raised, /passport/);

  const closed = renderToStaticMarkup(
    createElement(MorningCheckInCard, {
      item: { ...item, state: "dismissed", armed: false, citations: [] },
      t,
      busy: false,
      onDismiss() {},
    }),
  );
  assert.doesNotMatch(closed, new RegExp(dentist));
  assert.doesNotMatch(closed, /Dismiss/);
});
