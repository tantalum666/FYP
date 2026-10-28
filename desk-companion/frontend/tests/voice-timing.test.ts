import assert from "node:assert/strict";
import test from "node:test";
import { CaptureTimeline, renderedAt } from "../src/workspace/voice-timing.ts";

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
