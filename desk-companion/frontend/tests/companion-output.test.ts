import assert from "node:assert/strict";
import test from "node:test";
import { mouthLevel, subscribePlayback } from "../src/companion/output.ts";
test("mouth ignores expired/future and nonfinite speaker samples", () => {
  assert.ok(Math.abs(mouthLevel({ level: 0.1, at: 1000 }, 1000) - 0.7) < 1e-12);
  assert.equal(mouthLevel({ level: 9, at: 1000 }, 1100), 1);
  assert.equal(mouthLevel({ level: 0.1, at: 1000 }, 1300), 0);
  assert.equal(mouthLevel({ level: 0.1, at: 1400 }, 1300), 0);
  assert.equal(mouthLevel({ level: NaN, at: 1000 }, 1100), 0);
  assert.equal(mouthLevel({ level: -1, at: 1000 }, 1100), 0);
});
test("presentation bridge accepts bounded shape only and removes listeners on disposal", () => {
  const beforeWindow = globalThis.window,
    beforeChannel = globalThis.BroadcastChannel;
  const eventTarget = new EventTarget();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: eventTarget,
  });
  Object.defineProperty(globalThis, "BroadcastChannel", {
    configurable: true,
    value: undefined,
  });
  const received: unknown[] = [];
  try {
    const dispose = subscribePlayback((s) => received.push(s));
    const send = (detail: unknown) => {
      const e = new Event("desk:avatar-playback");
      Object.assign(e, { detail });
      eventTarget.dispatchEvent(e);
    };
    send({ level: 0.05, at: 1234, transcript: "never accepted" });
    send({ level: NaN, at: 1234 });
    send({ level: "1", at: 1234 });
    send(null);
    assert.deepEqual(received, [{ level: 0.05, at: 1234 }]);
    dispose();
    send({ level: 0.2, at: 1250 });
    assert.equal(received.length, 1);
  } finally {
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: beforeWindow,
    });
    Object.defineProperty(globalThis, "BroadcastChannel", {
      configurable: true,
      value: beforeChannel,
    });
  }
});
