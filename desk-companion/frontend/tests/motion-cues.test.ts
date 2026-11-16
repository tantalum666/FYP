import assert from "node:assert/strict";
import test from "node:test";
import { MotionCues, GESTURE_SECONDS } from "../src/companion/motion-cues.ts";
import { aliceMotion } from "../src/companion/alice-motion.ts";

test("repeated taps do not restart a moving arm and later greetings vary", () => {
  const cues = new MotionCues();
  cues.hello(0);
  const first = cues.sample(0.2, "idle");
  cues.hello(0.3);
  cues.hello(1.7);
  assert.deepEqual(cues.sample(2, "idle"), first);
  assert.equal(cues.sample(5, "idle"), null);
  cues.hello(6);
  assert.equal(cues.sample(6.5, "idle")?.gesture, "nod");
  cues.hello(9);
  assert.equal(cues.sample(9.5, "idle")?.gesture, "curious");
});

test("a conversation preempts idle fidgeting and includes quiet gaps", () => {
  const cues = new MotionCues();
  assert.equal(cues.sample(12, "idle")?.gesture, "glance");
  assert.equal(cues.sample(13, "listening"), null);
  assert.equal(cues.sample(13.5, "listening")?.gesture, "curious");
  assert.equal(cues.sample(18, "listening"), null);
  assert.equal(cues.sample(21, "listening"), null);
  assert.equal(cues.sample(23, "listening")?.gesture, "nod");
  assert.equal(cues.sample(24, "speaking"), null);
  assert.equal(cues.sample(24.5, "speaking")?.gesture, "explain");
  assert.equal(cues.sample(25, "idle"), null);
  assert.equal(cues.sample(30, "idle"), null);
});

test("an automatic glance does not swallow a person's greeting", () => {
  const cues = new MotionCues();
  assert.equal(cues.sample(12, "idle")?.gesture, "glance");
  cues.hello(12.5);
  assert.equal(cues.sample(13, "idle")?.gesture, "wave");
});

test("a visibly settled greeting immediately accepts the next tap", () => {
  const cues = new MotionCues();
  cues.hello(0);
  const time = GESTURE_SECONDS.wave - 0.001;
  const previous = cues.sample(time, "idle")!;
  assert.equal(aliceMotion(time, previous).gesture, null);
  cues.hello(time);
  assert.equal(cues.sample(time + 0.01, "idle")?.gesture, "nod");
});

test("gesture sampling does not queue missed gestures after a long pause", () => {
  const cues = new MotionCues();
  cues.sample(1, "speaking");
  assert.equal(cues.sample(1.5, "speaking")?.gestureAt, 1.5);
  assert.equal(cues.sample(900, "speaking")?.gestureAt, 900);
  assert.equal(cues.sample(901, "speaking")?.gestureAt, 900);
  assert.equal(cues.sample(NaN, "idle"), null);
});

test("every gesture returns to rest without endpoint jumps or unbounded rotation", () => {
  for (const [name, duration] of Object.entries(GESTURE_SECONDS)) {
    const gesture = name as keyof typeof GESTURE_SECONDS;
    const options = { gesture, gestureAt: 0 };
    for (const time of [-1, 0, duration, duration + 5])
      assert.deepEqual(aliceMotion(time, options), aliceMotion(time));
    for (let age = 0; age < duration; age += 0.02) {
      const pose = aliceMotion(age, options).pose;
      const next = aliceMotion(age + 0.02, options).pose;
      for (const name of Object.keys(pose) as (keyof typeof pose)[])
        for (let axis = 0; axis < 3; axis++) {
          assert.ok(Number.isFinite(pose[name][axis]));
          assert.ok(
            Math.abs(pose[name][axis] - next[name][axis]) < 0.15,
            `${gesture} jumps at ${age}: ${name}`,
          );
        }
    }
  }
});
