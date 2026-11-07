import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import * as timing from "../src/workspace/voice-timing.ts";
import { microphoneConstraints } from "../src/workspace/media/microphone.ts";
function setup() {
  let played = 0,
    stopped = 0,
    streamStopped = 0,
    closed = 0;
  const events: any[] = [],
    messages: any[] = [];
  const chain = () => ({
    connect() {
      return this;
    },
    disconnect() {},
  });
  class Context {
    currentTime = 0;
    destination = {};
    audioWorklet = { addModule: async () => {} };
    resume = async () => {};
    close = async () => {
      closed++;
    };
    createMediaStreamSource = chain;
    createGain = () => ({ ...chain(), gain: { value: 1 } });
    createBuffer = (_: number, length: number, rate: number) => ({
      getChannelData: () => new Float32Array(length),
      duration: length / rate,
    });
    createBufferSource = () => ({
      ...chain(),
      ...chain(),
      start() {
        played++;
      },
      stop() {
        stopped++;
      },
      buffer: null,
      onended: null,
    });
  }
  class Socket {
    static OPEN = 1;
    static last: any;
    readyState = 1;
    bufferedAmount = 0;
    onmessage: any;
    onopen: any;
    onclose: any;
    onerror: any;
    constructor() {
      Socket.last = this;
    }
    send(value: string) {
      messages.push(JSON.parse(value));
    }
    close() {
      this.readyState = 3;
    }
  }
  const globals = {
    AudioContext: Context,
    AudioWorkletNode: class {
      disconnect() {}
      port = { close() {} };
      connect() {
        return chain();
      }
    },
    WebSocket: Socket,
    navigator: {
      mediaDevices: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => streamStopped++ }],
        }),
      },
    },
  };
  const previous = Object.keys(globals).map(
    (key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const,
  );
  for (const [key, value] of Object.entries(globals))
    Object.defineProperty(globalThis, key, { configurable: true, value });
  const output: any = {};
  const source = readFileSync(
    new URL("../src/workspace/audio.ts", import.meta.url),
    "utf8",
  );
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
    },
  }).outputText;
  new Function("require", "exports", compiled)(
    () => ({
      ...timing,
      microphoneConstraints,
      OutputMeter: class {
        input = {};
        start() {}
        reset() {}
        close() {}
      },
    }),
    output,
  );
  const audio = new output.VoiceAudio((event: any) => events.push(event));
  return {
    audio,
    events,
    messages,
    socket: () => Socket.last,
    emit: (event: any) =>
      Socket.last.onmessage?.({ data: JSON.stringify(event) }),
    counts: () => ({ played, stopped, streamStopped, closed }),
    restore() {
      audio.close();
      for (const [key, descriptor] of previous) {
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else Reflect.deleteProperty(globalThis, key);
      }
    },
  };
}
test("interrupt drops queued and late audio for the old turn while a new turn can reply", async () => {
  const h = setup();
  try {
    await h.audio.start(
      async () => "fake-ticket",
      "en",
      "ws://protocol-fake.invalid",
    );
    h.emit({ type: "ready" });
    h.emit({ type: "turn_waiting", turn_id: 1 });
    h.emit({
      type: "audio",
      turn_id: 1,
      audio: "AAAAAA==",
      sample_rate: 24000,
    });
    assert.equal(h.counts().played, 1);
    h.audio.interrupt();
    assert.equal(h.counts().stopped, 1);
    h.emit({ type: "audio", turn_id: 1, audio: "AAAAAA==" });
    assert.equal(h.counts().played, 1);
    assert.deepEqual(h.messages, [{ type: "interrupt" }]);
    h.emit({ type: "turn_waiting", turn_id: 2 });
    h.emit({ type: "audio", turn_id: 2, audio: "AAAAAA==" });
    assert.equal(h.counts().played, 2);
    const late = h.socket().onmessage;
    h.audio.close();
    late({
      data: JSON.stringify({ type: "audio", turn_id: 2, audio: "AAAAAA==" }),
    });
    assert.equal(h.counts().played, 2);
    assert.equal(h.counts().streamStopped, 1);
    assert.equal(h.counts().closed, 1);
  } finally {
    h.restore();
  }
});

test("malformed PCM/base64 closes capture instead of throwing in a socket callback", async () => {
  for (const audio of ["AAAA", "*invalid*"]) {
    const h = setup();
    try {
      await h.audio.start(
        async () => "fake-ticket",
        "en",
        "ws://protocol-fake.invalid",
      );
      assert.doesNotThrow(() => h.emit({ type: "audio", audio }));
      assert.equal(h.counts().streamStopped, 1);
      assert.equal(h.counts().played, 0);
      assert.equal(h.events.at(-1).type, "error");
      assert.ok(
        h.events.some((event) =>
          ["VOICE_INVALID_AUDIO", "VOICE_INVALID_MESSAGE"].includes(event.code),
        ),
      );
    } finally {
      h.restore();
    }
  }
});
