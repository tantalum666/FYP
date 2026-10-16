import assert from "node:assert/strict";
import test from "node:test";
import { VoiceAudio } from "../src/workspace/audio.ts";
import { encodeVoiceImage, voiceImageSize } from "../src/workspace/vision.ts";

function engine() {
  const sent: Array<{ type: string }> = [];
  const audio = new VoiceAudio(() => {});
  const socket = {
    readyState: 1,
    bufferedAmount: 0,
    onclose: null,
    send: (raw: string) => sent.push(JSON.parse(raw)),
    close() {
      this.readyState = 3;
    },
  };
  Object.assign(audio, { ready: true, audioSent: true, socket });
  return { audio, sent };
}

test("frames are bounded to720p without distorting portrait or landscape", () => {
  assert.deepEqual(voiceImageSize(2560, 1440), { width: 1280, height: 720 });
  assert.deepEqual(voiceImageSize(1080, 1920), { width: 405, height: 720 });
  assert.throws(() => voiceImageSize(0, 100));
});

test("JPEG encoding reduces quality to fit the provider frame limit", () => {
  const original = globalThis.document;
  const quality: number[] = [];
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage() {} }),
    toDataURL: (_type: string, q: number) => {
      quality.push(q);
      return (
        "data:image/jpeg;base64," + (q > 0.6 ? "A".repeat(270000) : "AA==")
      );
    },
  };
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { createElement: () => canvas },
  });
  try {
    assert.equal(encodeVoiceImage({} as CanvasImageSource, 1920, 1080), "AA==");
    assert.deepEqual(quality, [0.8, 0.6]);
    assert.equal(canvas.width, 1280);
  } finally {
    Object.defineProperty(globalThis, "document", {
      configurable: true,
      value: original,
    });
  }
});

test("ending voice while the screen chooser is pending stops late tracks and sends no frame", async () => {
  const original = navigator.mediaDevices;
  let resolve!: (stream: MediaStream) => void;
  const pending = new Promise<MediaStream>((done) => {
    resolve = done;
  });
  let stopped = 0;
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getDisplayMedia: () => pending },
  });
  try {
    const { audio, sent } = engine();
    const start = audio.shareScreen();
    audio.close();
    resolve({
      getTracks: () => [{ stop: () => stopped++ }],
    } as unknown as MediaStream);
    await start;
    assert.equal(stopped, 1);
    assert.equal(sent.length, 0);
  } finally {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: original,
    });
  }
});

test("a selected image decoded after disconnect is closed without sending", async () => {
  const original = globalThis.createImageBitmap;
  let resolve!: (image: ImageBitmap) => void;
  const pending = new Promise<ImageBitmap>((done) => {
    resolve = done;
  });
  let closed = 0;
  globalThis.createImageBitmap = (() => pending) as typeof createImageBitmap;
  try {
    const { audio, sent } = engine();
    const upload = audio.shareImage({ type: "image/jpeg", size: 500 } as File);
    audio.close();
    resolve({ width: 32, height: 24, close: () => closed++ } as ImageBitmap);
    await upload;
    assert.equal(closed, 1);
    assert.equal(sent.length, 0);
  } finally {
    globalThis.createImageBitmap = original;
  }
});
