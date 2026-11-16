import assert from "node:assert/strict";
import test from "node:test";
import {
  aliceMotion,
  blinkWeight,
  GREETING_SECONDS,
} from "../src/companion/alice-motion.ts";
import {
  reportInteraction,
  subscribeInteraction,
} from "../src/companion/interaction.ts";

test("a greeting lifts the chosen hand then fully returns to its current idle pose", () => {
  for (const side of ["left", "right"] as const) {
    const options = { gesture: "wave" as const, gestureAt: 1, waveSide: side };
    const peak = aliceMotion(2.5, options);
    assert.equal(peak.gesture, "wave");
    assert.ok(Math.abs(peak.pose[`${side}LowerArm`][2]) > 1);
    assert.ok(peak.smile > 0.1);
    for (const time of [0, 1, 1 + GREETING_SECONDS, 100])
      assert.deepEqual(aliceMotion(time, options), aliceMotion(time));
  }
});

test("state gestures stay bounded and never introduce root or foot translation", () => {
  for (const state of [
    "idle",
    "listening",
    "thinking",
    "speaking",
    "connecting",
    "not_configured",
  ]) {
    for (let time = 0; time <= 120; time += 0.1) {
      const motion = aliceMotion(time, {
        state,
        lookX: 50,
        lookY: -50,
        gesture: "wave",
        gestureAt: 1,
      });
      for (const [bone, angles] of Object.entries(motion.pose)) {
        assert.doesNotMatch(bone, /foot|leg|hips|root/i);
        assert.ok(
          angles.every(
            (value) =>
              Number.isFinite(value) &&
              Math.abs(value) < (bone.endsWith("LowerArm") ? 2.5 : 1.5),
          ),
        );
      }
      assert.ok(blinkWeight(time) >= 0 && blinkWeight(time) <= 1);
    }
  }
  assert.equal(aliceMotion(1, { state: "connecting" }).state, "thinking");
  assert.equal(aliceMotion(1, { state: "unknown" }).state, "idle");
  assert.ok(
    aliceMotion(NaN, { lookX: Infinity }).pose.head.every(Number.isFinite),
  );
  assert.notDeepEqual(
    aliceMotion(5, { state: "listening" }).pose,
    aliceMotion(5).pose,
  );
  assert.notDeepEqual(
    aliceMotion(5, { state: "speaking" }).pose,
    aliceMotion(5).pose,
  );
});

test("a hidden conversation releases its cue without clearing another active conversation", () => {
  const first = Symbol(),
    second = Symbol();
  const states: unknown[] = [];
  const unsubscribe = subscribeInteraction((state) => states.push(state));
  try {
    reportInteraction(first, "thinking");
    reportInteraction(second, "listening");
    reportInteraction(first, null);
    assert.deepEqual(states, [null, "thinking", "listening"]);
    reportInteraction(second, "speaking");
    const late: unknown[] = [];
    const stop = subscribeInteraction((state) => late.push(state));
    assert.deepEqual(late, ["speaking"]);
    stop();
    reportInteraction(second, null);
    assert.deepEqual(late, ["speaking"]);
    assert.equal(states.at(-1), null);
    unsubscribe();
    const count = states.length;
    reportInteraction(first, "thinking");
    assert.equal(states.length, count);
  } finally {
    unsubscribe();
    reportInteraction(first, null);
    reportInteraction(second, null);
  }
});
