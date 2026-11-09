import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { ComputerUseComposer } =
  await import("../src/workspace/ComputerUseComposer.tsx");
const { JobActionCard } = await import("../src/workspace/JobActionCard.tsx");

test("screen sharing is explicit and preparation does not promise a booking", () => {
  const html = renderToStaticMarkup(
    createElement(ComputerUseComposer, {
      t: (en: string) => en,
      available: true,
      initialGoal: "Compare a public page",
      onPrepared() {},
    }),
  );
  assert.match(html, /page screenshots in the cloud/);
  assert.match(html, /Uses your assistant allowance/);
  assert.doesNotMatch(html, /OpenAI|model turns|API credit/);
  assert.doesNotMatch(html, /checked=""/);
  assert.match(html, /disabled=""/);
});

test("verified browser bytes are presented as owner review, not a completed purchase", () => {
  const html = renderToStaticMarkup(
    createElement(JobActionCard, {
      job: {
        id: "fixture",
        action: "computer_use",
        state: "succeeded",
        updated_at: new Date().toISOString(),
        cancel_requested: false,
        request: {
          title: "Review cart",
          content: "Cart",
          artifact_id: "fixture",
          start_url: "demo:shopping",
        },
        result: {
          verified: true,
          outcome: "needs_owner",
          readback: { reason: "final_submission_needs_owner" },
        },
      },
      t: (en: string) => en,
      busy: false,
      cancelling: false,
      fresh: true,
      available: true,
      onAction() {},
      onContinue() {},
    }),
  );
  assert.match(html, /Needs you/);
  assert.match(html, /Continue from this page/);
  assert.doesNotMatch(
    html,
    /Check the saved file|Save a new file|purchase completed/i,
  );
});
