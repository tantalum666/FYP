import assert from "node:assert/strict";
import test from "node:test";
import {
  createCalendarReader,
  readCalendarViews,
} from "../src/phone/calendar-reader.ts";
import type { Snapshot } from "../src/types.ts";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
};
const home = { start: "2026-10-27T16:00:00Z", end: "2026-11-03T16:00:00Z" };
const snapshot = { revision: 1, occurrences: [] } as unknown as Snapshot;

test("a day inside the home week uses one calendar request", async () => {
  const calls: unknown[] = [];
  const result = await readCalendarViews(
    { start: "2026-10-28T16:00:00Z", end: "2026-10-29T16:00:00Z" },
    home,
    async (range) => {
      calls.push(range);
      return snapshot;
    },
  );
  assert.deepEqual(calls, [home]);
  assert.equal(result.home, snapshot);
  assert.equal(result.plan, snapshot);
});

test("an outside month loads both ranges concurrently without substituting the home week", async () => {
  const a = deferred<Snapshot>(),
    b = deferred<Snapshot>();
  const calls: unknown[] = [];
  const month = { start: "2026-10-01T00:00:00Z", end: "2026-11-01T00:00:00Z" };
  const reading = readCalendarViews(month, home, (range) => {
    calls.push(range);
    return range === home ? a.promise : b.promise;
  });
  assert.deepEqual(calls, [home, month]);
  const plan = { ...snapshot, revision: 2 };
  b.resolve(plan);
  a.resolve(snapshot);
  assert.deepEqual(await reading, { home: snapshot, plan });
});

test("save and polling refresh bursts coalesce; an older response cannot overwrite the new state", async () => {
  const a = deferred<number>(),
    b = deferred<number>();
  const accepted: number[] = [];
  let calls = 0;
  const reader = createCalendarReader(
    () => (++calls === 1 ? a.promise : b.promise),
    (value) => accepted.push(value),
    assert.fail,
  );
  const reading = reader.refresh();
  for (let i = 0; i < 10; i++) void reader.refresh();
  assert.equal(calls, 1);
  a.resolve(1);
  await Promise.resolve();
  assert.equal(calls, 2);
  assert.deepEqual(accepted, []);
  b.resolve(2);
  await reading;
  assert.deepEqual(accepted, [2]);
});

test("leaving a date, session, or hidden screen discards pending responses and queued work", async () => {
  const a = deferred<number>();
  let calls = 0;
  const reader = createCalendarReader(
    () => {
      calls++;
      return a.promise;
    },
    () => assert.fail("disposed read reached UI"),
    assert.fail,
  );
  const reading = reader.refresh();
  void reader.refresh();
  reader.dispose();
  a.resolve(1);
  await reading;
  await reader.refresh();
  assert.equal(calls, 1);
});

test("a failed calendar read can recover on the next explicit refresh", async () => {
  const errors: unknown[] = [],
    accepted: number[] = [];
  let calls = 0;
  const failure = new Error("offline");
  const reader = createCalendarReader(
    async () => {
      if (++calls === 1) throw failure;
      return 2;
    },
    (value) => accepted.push(value),
    (error) => errors.push(error),
  );
  await reader.refresh();
  await reader.refresh();
  assert.deepEqual(errors, [failure]);
  assert.deepEqual(accepted, [2]);
});
