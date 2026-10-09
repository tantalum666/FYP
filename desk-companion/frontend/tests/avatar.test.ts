import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createHash } from "node:crypto";
import {
  assistantState,
  inspectVrm,
  playbackLevel,
  rmsLevel,
} from "../src/avatar/model.ts";
import { PlaybackMeter } from "../src/avatar/playback.ts";
import type { WorkspaceSnapshot } from "../src/workspace/types.ts";

const snapshot = () =>
  ({
    voice: { active: false, state: "idle" },
    posture: {
      connected: true,
      preferences: { enabled: true },
      paused: false,
      snooze_until: 0,
      feedback: { outcome: "waiting", source: "live", created_at: 95 },
    },
  }) as WorkspaceSnapshot;

test("offline, paused, snoozed and replay posture cannot create a live character alert", () => {
  const data = snapshot();
  assert.equal(assistantState(data, false, 100), "alert");
  assert.equal(assistantState(data, true, 100), "disconnected");
  data.posture.paused = true;
  assert.equal(assistantState(data, false, 100), "idle");
  data.posture.paused = false;
  data.posture.snooze_until = 110;
  assert.equal(assistantState(data, false, 100), "idle");
  data.posture.snooze_until = 0;
  data.posture.feedback!.source = "replay";
  assert.equal(assistantState(data, false, 100), "idle");
});
test("live voice takes precedence and unknown provider states have a bounded fallback", () => {
  const data = snapshot();
  data.voice.active = true;
  data.voice.state = "thinking";
  assert.equal(assistantState(data, false, 100), "thinking");
  data.voice.state = "unexpected_provider_value";
  assert.equal(assistantState(data, false, 100), "idle");
  assert.equal(assistantState(null, false, 100), "disconnected");
});
test("mouth stops after missing playback and rejects invalid or future amplitude", () => {
  assert.equal(playbackLevel({ level: 0.5, at: 900 }, 1000), 0.5);
  assert.equal(playbackLevel({ level: 0.5, at: 699 }, 1000), 0);
  assert.equal(playbackLevel({ level: 1, at: 1101 }, 1000), 0);
  assert.equal(playbackLevel({ level: NaN, at: 1000 }, 1000), 0);
  assert.equal(playbackLevel({ level: 99, at: 1000 }, 1000), 1);
  assert.equal(playbackLevel(null, 1000), 0);
});
test("output RMS ignores silence and never makes invalid audio a full-open mouth", () => {
  assert.equal(rmsLevel(new Float32Array(512)), 0);
  assert.equal(rmsLevel(new Float32Array([NaN])), 0);
  assert.equal(rmsLevel(new Float32Array()), 0);
  assert.ok(rmsLevel(new Float32Array([0.1, -0.1])) > 0.5);
  assert.equal(rmsLevel(new Float32Array([10])), 1);
});
function glb(json: object) {
  let text = JSON.stringify(json);
  while (text.length % 4) text += " ";
  const buffer = new ArrayBuffer(20 + text.length),
    v = new DataView(buffer);
  v.setUint32(0, 0x46546c67, true);
  v.setUint32(4, 2, true);
  v.setUint32(8, buffer.byteLength, true);
  v.setUint32(12, text.length, true);
  v.setUint32(16, 0x4e4f534a, true);
  new Uint8Array(buffer, 20).set(new TextEncoder().encode(text));
  return buffer;
}
test("local VRMs cannot fetch external images, buffers or unsupported codecs", () => {
  const extensions = { VRMC_vrm: { meta: { name: "Local" } } };
  assert.equal(inspectVrm(glb({ extensions })).name, "Local");
  assert.throws(
    () =>
      inspectVrm(
        glb({
          extensions,
          images: [{ uri: "https://example.com/private.png" }],
        }),
      ),
    /MODEL_EXTERNAL_RESOURCE/,
  );
  assert.throws(
    () =>
      inspectVrm(
        glb({
          extensions,
          buffers: [{ uri: "data:application/octet-stream;base64,AAAA" }],
        }),
      ),
    /MODEL_EXTERNAL_RESOURCE/,
  );
  assert.throws(
    () =>
      inspectVrm(
        glb({ extensions, extensionsRequired: ["KHR_draco_mesh_compression"] }),
      ),
    /MODEL_EXTENSION/,
  );
  assert.throws(
    () => inspectVrm(glb({ asset: { version: "2.0" } })),
    /MODEL_NOT_VRM/,
  );
});
test("bundled avatar matches the pinned upstream asset and permits redistribution", () => {
  const b = fs.readFileSync(
    new URL("../public/avatars/pixiv-sample.vrm", import.meta.url),
  );
  assert.equal(
    createHash("sha256").update(b).digest("hex"),
    "12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2",
  );
  const info = inspectVrm(
    b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength),
  );
  assert.equal(info.meta.allowRedistribution, true);
  assert.equal(info.meta.avatarPermission, "everyone");
  assert.equal(info.meta.licenseUrl, "https://vrm.dev/licenses/1.0/");
});
test("playback meter samples actual output and resets immediately on interruption / close", async () => {
  const samples: number[] = [];
  const analyser = {
    fftSize: 0,
    connect: () => {},
    disconnect: () => {},
    getFloatTimeDomainData: (values: Float32Array) => values.fill(0.1),
  };
  const meter = new PlaybackMeter(
    {
      createAnalyser: () => analyser,
      destination: {},
    } as unknown as AudioContext,
    (s) => samples.push(s.level),
    false,
  );
  meter.start();
  await new Promise((resolve) => setTimeout(resolve, 90));
  assert.ok(samples.some((n) => n > 0.5));
  meter.reset();
  assert.equal(samples.at(-1), 0);
  const count = samples.length;
  await new Promise((resolve) => setTimeout(resolve, 90));
  assert.equal(samples.length, count);
  meter.close();
  const closed = samples.length;
  meter.start();
  await new Promise((resolve) => setTimeout(resolve, 50));
  assert.equal(samples.length, closed);
});
