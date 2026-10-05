import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import { DateTime } from "luxon";
import { busyMinutes, lunarDate } from "../src/workspace/calendarExtras.ts";
import type { Occurrence } from "../src/types.ts";
import type { Snapshot } from "../src/types.ts";
import type { PostureSnapshot } from "../src/workspace/types.ts";
import { displayPrivacy } from "../src/device/privacy.ts";

test("audio worklet retains fractional phase across 128-sample blocks", () => {
  for (const rate of [44100, 48000]) {
    let Constructor: any;
    let emitted = 0;
    const Processor = class {
      port = {
        postMessage: (data: ArrayBuffer) => {
          emitted += data.byteLength / 2;
        },
      };
    };
    vm.runInNewContext(
      fs.readFileSync(
        new URL("../public/audio-capture.js", import.meta.url),
        "utf8",
      ),
      {
        AudioWorkletProcessor: Processor,
        sampleRate: rate,
        registerProcessor: (_: string, value: any) => (Constructor = value),
        DataView,
        ArrayBuffer,
      },
    );
    const processor = new Constructor();
    for (let index = 0; index < rate * 2; index += 128) {
      processor.process([[new Float32Array(Math.min(128, rate * 2 - index))]]);
    }
    assert.ok(
      Math.abs(emitted + processor.chunk.length - 32000) <= 1,
      `${rate} Hz must preserve two seconds of audio`,
    );
    assert.ok(
      processor.buffer.length < 4,
      "resampling buffer must remain bounded",
    );
  }
});
test("busy duration merges overlaps, clips to day, and ignores completed events", () => {
  const day = DateTime.fromISO("2026-10-02", { zone: "Asia/Hong_Kong" });
  const event = (start: string, end: string, completed = false) =>
    ({ start, end, busy: true, completed }) as Occurrence;
  const events = [
    event("2026-10-02T00:00:00Z", "2026-10-02T02:00:00Z"),
    event("2026-10-02T01:00:00Z", "2026-10-02T03:00:00Z"),
    event("2026-10-01T15:00:00Z", "2026-10-01T17:00:00Z"),
    event("2026-10-02T10:00:00Z", "2026-10-02T12:00:00Z", true),
  ];
  assert.equal(busyMinutes(events, day), 240);
});
test("lunar day is computed in the selected calendar timezone", () => {
  const day = DateTime.fromISO("2026-09-25", { zone: "Asia/Hong_Kong" });
  assert.match(lunarDate(day, "zh"), /八月/);
  assert.match(lunarDate(day, "zh"), /15/);
});

test("a stale posture connection masks private content in a previously loaded display snapshot", () => {
  const privateEvent = {
    title: "Private title",
    notes: "Private notes",
    location: "Private place",
    visibility: "private",
  };
  const visible = {
    ...privateEvent,
    title: "Public title",
    visibility: "displayable",
  };
  const snapshot = {
    occurrences: [privateEvent, visible],
    reminders: [
      { title: "Private title", visibility: "private" },
      { title: "Public title", visibility: "displayable" },
    ],
  } as Snapshot;
  const posture = {
    connected: true,
    status: "within_reference",
    preferences: { enabled: true, privacy_when_away: true },
  } as PostureSnapshot;
  assert.equal(displayPrivacy(snapshot, posture, false), snapshot);
  const masked = displayPrivacy(snapshot, posture, true)!;
  assert.equal(masked.occurrences[0].title, "");
  assert.equal(masked.occurrences[0].notes, "");
  assert.equal(masked.occurrences[0].location, "");
  assert.equal(masked.occurrences[1].title, "Public title");
  assert.equal(masked.reminders[0].title, "");
  assert.equal(masked.reminders[1].title, "Public title");
  assert.equal(
    snapshot.occurrences[0].title,
    "Private title",
    "projection must not corrupt the editable source",
  );
});
