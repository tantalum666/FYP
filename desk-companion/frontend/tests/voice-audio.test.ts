import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
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
      port = {};
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
      PlaybackMeter: class {
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
test("protocol-fake interrupt suppresses all late audio until explicit hear again", async () => {
  const h = setup();
  try {
    await h.audio.start(
      async () => "fake-ticket",
      "en",
      "ws://protocol-fake.invalid",
    );
    h.emit({ type: "ready" });
    h.emit({ type: "audio", audio: "AAAAAA==", sample_rate: 24000 });
    assert.equal(h.counts().played, 1);
    h.audio.interrupt();
    assert.equal(h.counts().stopped, 1);
    h.emit({ type: "turn_complete" });
    h.emit({ type: "transcript", role: "user", text: "new input" });
    h.emit({ type: "audio", audio: "AAAAAA==" });
    assert.equal(h.counts().played, 1);
    assert.equal(h.events.at(-1).suppressed, true);
    assert.deepEqual(
      h.messages,
      [{ type: "interrupt" }],
      "no Work or physical-output cancellation",
    );
    h.audio.hearAgain();
    h.emit({ type: "audio", audio: "AAAAAA==" });
    assert.equal(h.counts().played, 2);
    const late = h.socket().onmessage;
    h.audio.close();
    late({ data: JSON.stringify({ type: "audio", audio: "AAAAAA==" }) });
    assert.equal(h.counts().played, 2);
    assert.equal(h.counts().streamStopped, 1);
    assert.equal(h.counts().closed, 1);
  } finally {
    h.restore();
  }
});
test("ordinary provider speech-start does not mute new responses; explicit mute stays latched", async () => {
  const h = setup();
  try {
    await h.audio.start(
      async () => "fake-ticket",
      "zh",
      "ws://protocol-fake.invalid",
    );
    h.emit({ type: "interrupted" });
    h.emit({ type: "audio", audio: "AAAAAA==" });
    assert.equal(h.counts().played, 1);
    h.audio.interrupt();
    h.emit({ type: "interrupted" });
    h.emit({ type: "audio", audio: "AAAAAA==" });
    assert.equal(h.counts().played, 1);
    h.emit({ type: "ended" });
    assert.equal(h.socket().readyState, 3);
    assert.equal(h.socket().onmessage, null);
    assert.equal(h.counts().streamStopped, 1);
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
      assert.ok(h.events.some((event) => event.code === "VOICE_AUDIO_INVALID"));
    } finally {
      h.restore();
    }
  }
});
