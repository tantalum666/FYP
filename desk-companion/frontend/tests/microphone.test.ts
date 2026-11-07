import assert from "node:assert/strict";
import test from "node:test";
import {
  microphoneConstraints,
  selectedMicrophone,
  selectMicrophone,
} from "../src/workspace/media/microphone.ts";

test("an explicitly selected microphone stays exact across preview, wake and voice capture", (t) => {
  const values = new Map<string, string>();
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    },
  });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "localStorage", original);
    else Reflect.deleteProperty(globalThis, "localStorage");
  });
  assert.equal(microphoneConstraints().deviceId, undefined);
  selectMicrophone("fictional-built-in-input");
  assert.equal(selectedMicrophone(), "fictional-built-in-input");
  assert.deepEqual(microphoneConstraints().deviceId, {
    exact: "fictional-built-in-input",
  });
  selectMicrophone("");
  assert.equal(microphoneConstraints().deviceId, undefined);
});

test("blocked browser storage keeps the explicit microphone for this page", (t) => {
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get: () => {
      throw new Error("Storage blocked");
    },
  });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "localStorage", original);
    else Reflect.deleteProperty(globalThis, "localStorage");
  });
  selectMicrophone("input");
  assert.equal(selectedMicrophone(), "input");
  assert.deepEqual(microphoneConstraints().deviceId, { exact: "input" });
  assert.equal(microphoneConstraints().channelCount, 1);
});
