import assert from "node:assert/strict";
import test from "node:test";
import { taskRecoveryGuidance } from "../src/workspace/jobTypes.ts";

test("an unknown file result is distinct from a write that never happened", () => {
  const unknown = taskRecoveryGuidance({ state: "unknown", action: "save_note" });
  const cancelled = taskRecoveryGuidance({ state: "cancelled", action: "save_note" });
  const review = taskRecoveryGuidance({ state: "review", action: "save_note" });
  const checked = taskRecoveryGuidance({
    state: "succeeded",
    action: "save_note",
    result: { verified: true },
  });
  assert.equal(unknown?.kind, "unknown");
  assert.equal(cancelled?.kind, "nothing_written");
  assert.equal(review?.kind, "needs_approval");
  assert.equal(checked?.kind, "checked");
  assert.notEqual(unknown?.text[0], cancelled?.text[0]);
  assert.match(unknown?.text[0] ?? "", /Check result/);
  assert.match(review?.text[0] ?? "", /does not approve/);
  assert.match(checked?.text[0] ?? "", /not written again/);
  assert.equal(
    taskRecoveryGuidance({ state: "running", action: "save_note" }),
    null,
  );
});
