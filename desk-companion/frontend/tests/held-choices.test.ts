import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { heldAssumption } from "../src/workspace/heldChoice.ts";

test("a pending assumption is not the choice being held", () => {
  const both = heldAssumption({
    current: { assumption: "Budget stays HKD 2000" },
    pending: { assumption: "Budget stays HKD 1500" },
  });
  assert.equal(both.held, "Budget stays HKD 2000");
  assert.equal(both.waiting, "Budget stays HKD 1500");
  assert.deepEqual(
    heldAssumption({ current: null, pending: { assumption: "Budget stays HKD 2000" } }),
    { held: null, waiting: "Budget stays HKD 2000" },
  );
});

test("the tasks page shows held choices and does not describe a sent or paid result", () => {
  const panel = fs.readFileSync(
    new URL("../src/workspace/HeldChoicePanel.tsx", import.meta.url),
    "utf8",
  );
  const app = fs.readFileSync(new URL("../src/workspace/WorkTools.tsx", import.meta.url), "utf8");
  assert.match(panel, /Not the current choice until you approve this wording/);
  assert.match(panel, /does not send mail, buy, or book anything/);
  assert.match(panel, /Approve this wording/);
  assert.match(panel, /Previous wording/);
  assert.doesNotMatch(panel, /sent the|paid|purchased|booked a|order placed/i);
  assert.match(app, /HeldChoicePanel/);
});
