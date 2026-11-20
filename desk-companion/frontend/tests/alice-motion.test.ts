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
import { JointMotion } from "../src/companion/motion-response.ts";
import { RenderCadence } from "../src/companion/render-cadence.ts";

test("a glance acquires its target before the head and shoulders turn", () => {
  const t = 0.18;
  const first = aliceMotion(t, { gesture: "glance", gestureAt: 0 });
  const neutral = aliceMotion(t);
  assert.ok(first.gaze.yaw > 20);
  assert.ok(Math.abs(first.pose.head[1] - neutral.pose.head[1]) < 0.002);
  assert.equal(first.pose.chest[1], neutral.pose.chest[1]);
  const later = aliceMotion(1.3, { gesture: "glance", gestureAt: 0 });
  assert.ok(later.pose.head[1] > 0.2 && later.gaze.yaw < first.gaze.yaw);
});

test("a mid-gesture interruption preserves velocity then settles", () => {
  const joint = new JointMotion("head");
  joint.update([1, 0, 0], 0.07);
  const before = joint.angles[0];
  const moving = joint.update([1, 0, 0], 0.001)[0];
  const interrupted = joint.update([0, 0, 0], 0.001)[0];
  assert.ok(
    interrupted > moving &&
      Math.abs((interrupted - moving) / (moving - before) - 1) < 0.04,
  );
  for (let i = 0; i < 60; i++) joint.update([0, 0, 0], 1 / 30);
  assert.ok(Math.abs(joint.angles[0]) < 1e-8);
});

test("display timestamp jitter preserves the 30 Hz cadence and hidden time is excluded", () => {
  for (const hz of [60, 120]) {
    const cadence = new RenderCadence();
    const deltas = [];
    for (let frame = 0; frame <= 10 * hz; frame++) {
      const at = (frame * 1000) / hz + 0.7 * Math.sin(frame * 1.67);
      const delta = cadence.sample(at);
      if (delta !== null) deltas.push(delta);
    }
    assert.equal(deltas.length, 301);
    assert.ok(deltas.slice(1).every((dt) => dt > 0.03 && dt < 0.036));
    assert.equal(cadence.sample(17000), 0.25);
    assert.equal(cadence.sample(17001), null);
    cadence.reset();
    assert.equal(cadence.sample(30000), 0);
  }
});

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
