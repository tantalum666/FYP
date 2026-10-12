import test from "node:test";
import assert from "node:assert/strict";
import {
  depthAt,
  gesturePose,
  weightsAt,
} from "../src/companion/depth-model.ts";

test("depth and skin weights stay continuous through neck, elbows, wrists and knees", () => {
  for (let y = 13; y < 1500; y += 5) {
    for (let x = 282; x < 740; x += 5) {
      const a = weightsAt(x, y);
      for (const b of [weightsAt(x + 5, y), weightsAt(x, y + 5)]) {
        for (const key of Object.keys(a) as (keyof typeof a)[]) {
          assert.ok(Number.isFinite(a[key]) && a[key] >= 0 && a[key] <= 1);
          assert.ok(
            Math.abs(a[key] - b[key]) < 0.13,
            `Hard skinning edge at ${x},${y}: ${key}`,
          );
        }
      }
      const depth = depthAt(x, y);
      assert.ok(Number.isFinite(depth) && depth >= 0 && depth < 0.13);
      assert.ok(Math.abs(depth - depthAt(x + 5, y)) < 0.006);
      assert.ok(Math.abs(depth - depthAt(x, y + 5)) < 0.006);
    }
  }
  assert.ok(depthAt(512, 159) > depthAt(325, 159) + 0.04);
});
test("click responses ease out to a neutral pose and wave toward the page interior", () => {
  for (const kind of ["nod", "wave", "step"] as const) {
    for (const side of ["left", "right"] as const) {
      for (const t of [0, 1.7, 3]) {
        const p = gesturePose(kind, t, side);
        assert.ok(Object.values(p).every((value) => Math.abs(value) < 0.00001));
      }
    }
  }
  const left = gesturePose("wave", 0.85, "left"),
    right = gesturePose("wave", 0.85, "right");
  assert.ok(left.armLeft > 0 && left.armRight === 0);
  assert.ok(right.armRight < 0 && right.armLeft === 0);
  assert.ok(gesturePose("nod", 0.85, "left").nod > 0);
  assert.ok(gesturePose("step", 0.85, "left").step > 0);
});
