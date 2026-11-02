import assert from "node:assert/strict";
import test from "node:test";
import { LocalCapture } from "../src/workspace/media/localCapture.ts";
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function media() {
  let stopped = 0;
  const stream = {
    getTracks: () => [{ stop: () => stopped++ }, { stop: () => stopped++ }],
  } as unknown as MediaStream;
  return { stream, stopped: () => stopped };
}
test("local devices are requested explicitly and all tracks are released on stop", async () => {
  const fixture = media();
  let calls = 0;
  const owner = new LocalCapture(async () => {
    calls++;
    return fixture.stream;
  });
  assert.equal(calls, 0);
  assert.equal(
    await owner.start({ video: true, audio: false }),
    fixture.stream,
  );
  assert.ok(owner.owns(fixture.stream));
  assert.equal(calls, 1);
  owner.stop();
  owner.stop();
  assert.equal(fixture.stopped(), 2);
  assert.equal(owner.owns(fixture.stream), false);
});
test("a permission grant arriving after close is released without reactivating preview", async () => {
  const request = deferred<MediaStream>();
  const fixture = media();
  const owner = new LocalCapture(() => request.promise);
  const pending = owner.start({ video: true });
  owner.stop();
  request.resolve(fixture.stream);
  assert.equal(await pending, null);
  assert.equal(fixture.stopped(), 2);
  assert.equal(owner.pending, false);
});
test("out-of-order permission completions retain only the latest device request", async () => {
  const older = deferred<MediaStream>(),
    newer = deferred<MediaStream>();
  const a = media(),
    b = media();
  let calls = 0;
  const owner = new LocalCapture(() =>
    ++calls === 1 ? older.promise : newer.promise,
  );
  const first = owner.start({ video: true });
  const second = owner.start({ video: true });
  older.resolve(a.stream);
  assert.equal(await first, null);
  assert.equal(owner.pending, true);
  assert.equal(a.stopped(), 2);
  newer.resolve(b.stream);
  assert.equal(await second, b.stream);
  assert.equal(owner.pending, false);
  assert.ok(owner.owns(b.stream));
  assert.equal(b.stopped(), 0);
  owner.stop();
  assert.equal(b.stopped(), 2);
});
test("stale denial is ignored while a current permission failure stays actionable", async () => {
  const stale = deferred<MediaStream>();
  const owner = new LocalCapture(() => stale.promise);
  const pending = owner.start({ audio: true });
  owner.stop();
  stale.reject(new Error("denied"));
  assert.equal(await pending, null);
  const current = new LocalCapture(async () => {
    throw new Error("current denial");
  });
  await assert.rejects(current.start({ audio: true }), /current denial/);
  assert.equal(current.pending, false);
});
