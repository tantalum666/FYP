import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  canRevealRoutines,
  routineActions,
  routineItemTitle,
  uniqueDeliveries,
} from "../src/workspace/routineTypes.ts";
import type { RoutineItem, RoutineRun } from "../src/workspace/routineTypes.ts";

const panel = readFileSync(
  new URL("../src/workspace/RoutinesPanel.tsx", import.meta.url),
  "utf8",
);
test("only active/paused routines expose lifecycle actions", () => {
  assert.deepEqual(routineActions("active"), ["pause", "cancel"]);
  assert.deepEqual(routineActions("paused"), ["resume", "cancel"]);
  assert.deepEqual(routineActions("completed"), []);
  assert.deepEqual(routineActions("cancelled"), []);
});
test("delivery reveal fails closed for hidden, stale, locked or empty state", () => {
  assert.equal(canRevealRoutines(true, true, false, 1), true);
  assert.equal(canRevealRoutines(false, true, false, 1), false);
  assert.equal(canRevealRoutines(true, false, false, 1), false);
  assert.equal(canRevealRoutines(true, true, true, 1), false);
  assert.equal(canRevealRoutines(true, true, false, 0), false);
});
test("redacted or removed sources never display a cached title", () => {
  const item = {
    title: "Sensitive",
    available: true,
    redacted: false,
  } as RoutineItem;
  assert.equal(routineItemTitle(item, "Hidden", "Removed"), "Sensitive");
  assert.equal(
    routineItemTitle({ ...item, redacted: true }, "Hidden", "Removed"),
    "Hidden",
  );
  assert.equal(
    routineItemTitle({ ...item, available: false }, "Hidden", "Removed"),
    "Removed",
  );
});
test("notification deduplication uses delivery identity, not latest result identity", () => {
  const a = { id: "delivery-1", result_run_id: "run-1" } as RoutineRun;
  const b = { ...a, result_run_id: "run-2" };
  assert.deepEqual(uniqueDeliveries([a, b]), [b]);
  assert.equal(uniqueDeliveries([a, { ...b, id: "delivery-2" }]).length, 2);
});
test("private requests use component-memory recovery and a navigation guard", () => {
  assert.match(panel, /usePrivateMutation\(\)/);
  assert.match(panel, /useDraftGuard\(/);
  assert.doesNotMatch(
    panel,
    /(?:sessionStorage|localStorage|indexedDB|retryPending|pendingWrite)\b/,
  );
  assert.match(panel, /mutation\.retry\(\)/);
  assert.match(panel, /same request ID/);
});
test("mount and refresh read data without claiming a delivery", () => {
  const effect = panel.slice(
    panel.indexOf("useEffect(() =>"),
    panel.indexOf("function choose"),
  );
  assert.doesNotMatch(effect, /claim|reveal\(/);
  assert.equal((panel.match(/\/routines\/deliveries\/claim/g) ?? []).length, 1);
  assert.match(panel, /onClick=\{\(\) => void reveal\(\)\}/);
});
test("panel gates private content and offers bilingual schedule controls", () => {
  assert.match(panel, /personalContextVisible\(/);
  assert.match(panel, /token === generation\.current/);
  assert.match(panel, /setDeliveries\(\[\]\)/);
  assert.match(panel, /aria-labelledby=/);
  assert.match(panel, /aria-expanded=/);
  for (const label of [
    "Routine title",
    "First run (local time)",
    "Timezone (IANA)",
    "Reveal pending results",
    "Confirm cancellation",
    "定时事务标题",
    "首次运行（本地时间）",
    "确认取消",
  ])
    assert.ok(panel.includes(label), label);
  for (const frequency of ["once", "daily", "weekly"])
    assert.ok(panel.includes(`"${frequency}"`));
});

test("late claim results cannot reappear across concealment or identity changes", () => {
  assert.match(panel, /const epoch = scope\.current\.epoch/);
  assert.match(panel, /scope\.current\.epoch !== epoch/);
  assert.match(panel, /principal\.id/);
  assert.match(panel, /visibleOverride/);
  assert.match(panel, /setList\(null\)/);
  assert.match(panel, /selectedRef\.current/);
  assert.match(panel, /Discard draft/);
});
