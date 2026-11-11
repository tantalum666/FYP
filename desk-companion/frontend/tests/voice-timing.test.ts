import assert from "node:assert/strict";
import test from "node:test";
import {
  CaptureTimeline,
  PlaybackSchedule,
  renderedAt,
} from "../src/workspace/voice-timing.ts";

test("stale native timestamps cannot produce a false zero-latency success", () => {
  const result = renderedAt(
    {
      state: "running",
      currentTime: 2.4,
      outputLatency: 0.2,
      getOutputTimestamp: () => ({ contextTime: 2.4, performanceTime: 1200 }),
    },
    2,
    1_000_000,
  )!;
  assert.equal(result.source, "audio_context_estimate");
  assert.ok(Math.abs(result.at - 999800) < 0.01);
});

test("an enqueued buffer is not playback; output timestamp must pass its first sample", () => {
  const clock = {
    state: "running" as AudioContextState,
    currentTime: 3,
    getOutputTimestamp: () => ({ contextTime: 2.4, performanceTime: 9000 }),
  };
  assert.equal(renderedAt(clock, 2.5, 9200), null);
  clock.getOutputTimestamp = () => ({
    contextTime: 2.7,
    performanceTime: 9300,
  });
  assert.deepEqual(renderedAt(clock, 2.5, 9400), {
    at: 9100,
    source: "output_timestamp",
  });
});
test("suspended audio never counts as a reply and fallback is explicitly an estimate", () => {
  assert.equal(
    renderedAt({ state: "suspended", currentTime: 20 }, 2, 1000),
    null,
  );
  assert.equal(
    renderedAt(
      { state: "running", currentTime: 2.1, outputLatency: 0.2 },
      2,
      1000,
    ),
    null,
  );
  const result = renderedAt(
    { state: "running", currentTime: 2.4, outputLatency: 0.2 },
    2,
    1000,
  )!;
  assert.ok(Math.abs(result.at - 800) < 0.001);
  assert.equal(result.source, "audio_context_estimate");
});
test("capture endpoint excludes following silence and unknown boundaries stay labelled", () => {
  const capture = new CaptureTimeline();
  const pcm = new ArrayBuffer(1280);
  new Int16Array(pcm).fill(1000);
  assert.equal(capture.observe(pcm, 920), false);
  assert.equal(capture.observe(pcm, 960), false);
  assert.equal(capture.observe(pcm, 1000), false);
  for (let i = 1; i <= 9; i++)
    assert.equal(capture.observe(new ArrayBuffer(1280), 1000 + i * 40), false);
  assert.equal(capture.observe(new ArrayBuffer(1280), 1400), true);
  assert.deepEqual(capture.endpoint(520, 1600), {
    at: 1000,
    source: "capture_energy",
  });
  assert.deepEqual(new CaptureTimeline().endpoint(undefined, 1600), {
    at: 1600,
    source: "provider_event",
  });
});

test("short energy dips inside an utterance do not restart the voice turn", () => {
  const timeline = new CaptureTimeline();
  const voice = new Int16Array(640).fill(1000).buffer;
  const silence = new ArrayBuffer(1280);
  let starts = 0;
  for (let i = 0; i < 20; i++) {
    timeline.observe(i % 4 === 3 ? silence : voice, (i + 1) * 40);
    starts += Number(timeline.speechStarted);
  }
  assert.equal(starts, 1);
  for (let i = 0; i < 11; i++) timeline.observe(silence, 840 + i * 40);
  for (let i = 0; i < 3; i++) {
    timeline.observe(voice, 1280 + i * 40);
    starts += Number(timeline.speechStarted);
  }
  assert.equal(starts, 2);
});

test("packet jitter is absorbed in contiguous audio instead of repeated tiny gaps", () => {
  const schedule = new PlaybackSchedule();
  let previousEnd = 0;
  for (const arrival of [0, 0.06, 0.075, 0.14, 0.15, 0.21]) {
    const start = schedule.reserve(arrival, 0.04);
    if (previousEnd) assert.ok(Math.abs(start - previousEnd) < 1e-9);
    previousEnd = start + 0.04;
  }
  assert.equal(schedule.rebuffers, 0);
  const recovered = schedule.reserve(0.5, 0.04);
  assert.ok(recovered > 0.5);
  assert.equal(schedule.rebuffers, 1);
  schedule.reset();
  schedule.reserve(20, 0.04);
  assert.equal(schedule.rebuffers, 1); // A new reply is not a network underrun.
  assert.throws(() => schedule.reserve(20, 31), /AUDIO_CONNECTION_SLOW/);
});
