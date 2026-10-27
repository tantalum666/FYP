import assert from "node:assert/strict";
import test from "node:test";
import {
  APPEARANCE_KEY,
  MODELS,
  readAppearance,
  saveAppearance,
} from "../src/companion/appearance.ts";

test("Alice original is the default; rejected-study preferences cannot recolor it", (t) => {
  const old = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  const values = new Map([
    [
      "desk.a1.complete-vrm.v1",
      JSON.stringify({ model: "shino", palette: "silver", headRatio: 0.96 }),
    ],
  ]);
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: (k: string) => values.get(k) ?? null },
  });
  t.after(() => {
    if (old) Object.defineProperty(globalThis, "localStorage", old);
    else Reflect.deleteProperty(globalThis, "localStorage");
  });
  assert.deepEqual(readAppearance(), {
    model: "alice",
    palette: "original",
    headRatio: 1,
  });
  assert.equal(MODELS.alice.file, "/avatars/alice/alice-ready.vrm");
  values.set(
    APPEARANCE_KEY,
    JSON.stringify({ model: "victoria", palette: "silver", headRatio: 2 }),
  );
  assert.deepEqual(readAppearance(), {
    model: "victoria",
    palette: "silver",
    headRatio: 1.08,
  });
  values.set(APPEARANCE_KEY, '{"model":"__proto__"}');
  assert.equal(readAppearance().model, "alice");
  values.set(APPEARANCE_KEY, "bad-json");
  assert.equal(readAppearance().model, "alice");
  assert.equal(saveAppearance(readAppearance()), false);
});
