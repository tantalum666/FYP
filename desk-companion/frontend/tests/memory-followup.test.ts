import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  draftIsUnarmed,
  followUpActions,
  followUpErrorCopy,
  memoriesWithoutOpenFollowUp,
  type FollowUpDraft,
  type FollowUpView,
} from "../src/workspace/memoryFollowUp.ts";

register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { MemoryFollowUpCard, MemoryFollowUpDraftCard } =
  await import("../src/workspace/MemoryFollowUps.tsx");

const t = (en: string) => en;

const raised: FollowUpView = {
  id: "abc",
  memory_id: "def",
  state: "raised",
  version: 2,
  due_local: "2026-11-10T08:00",
  timezone: "Asia/Hong_Kong",
  body: "The Thursday dentist visit moved to Friday",
  memory_active: true,
  memory_updated: true,
  hold_reason: null,
  reason_en: "Alice raised this because the approved time has arrived.",
  reason_zh: "Alice 现在提醒你。",
  armed: true,
};

test("approval is required and a raised follow-up can be handled or snoozed", () => {
  assert.deepEqual(followUpActions("raised"), ["handled", "snooze", "dismissed"]);
  assert.deepEqual(followUpActions("pending"), ["dismissed"]);
  assert.deepEqual(followUpActions("held"), ["dismissed"]);
  assert.deepEqual(followUpActions("handled"), []);
  assert.equal(
    draftIsUnarmed({ armed: false, saved: false }),
    true,
  );
  assert.equal(draftIsUnarmed({ armed: true, saved: true }), false);
  assert.deepEqual(
    memoriesWithoutOpenFollowUp(
      [{ id: "open" }, { id: "free" }],
      [
        { memory_id: "open", state: "pending" },
        { memory_id: "done", state: "handled" },
      ],
    ).map((fact) => fact.id),
    ["free"],
  );
  assert.equal(followUpErrorCopy("FOLLOWUP_TIME_PAST")?.[0].includes("not arrived"), true);

  const draft: FollowUpDraft = {
    memory_id: "def",
    memory_version: 1,
    body: raised.body!,
    due_local: raised.due_local,
    timezone: raised.timezone,
    armed: false,
  };
  const preview = renderToStaticMarkup(
    createElement(MemoryFollowUpDraftCard, {
      draft,
      t,
      busy: false,
      onApprove() {},
      onDiscard() {},
    }),
  );
  assert.match(preview, /Nothing is scheduled until you approve/);
  assert.match(preview, /Approve follow-up/);
  assert.doesNotMatch(preview, /Handled/);

  const card = renderToStaticMarkup(
    createElement(MemoryFollowUpCard, {
      item: raised,
      t,
      busy: false,
      onResolve() {},
    }),
  );
  assert.match(card, /Friday/);
  assert.match(card, /Handled/);
  assert.match(card, /Remind me in an hour/);

  const waiting = renderToStaticMarkup(
    createElement(MemoryFollowUpCard, {
      item: { ...raised, state: "pending", body: "Still waiting" },
      t,
      busy: false,
      onResolve() {},
    }),
  );
  assert.match(waiting, /Still waiting/);
  assert.doesNotMatch(waiting, /Handled/);
});
