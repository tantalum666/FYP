import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";
import { VoiceAudio, type VoiceEvent } from "../src/workspace/audio.ts";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
};
function setup(
  t: TestContext,
  options: {
    resume?: Promise<void>;
    media?: Promise<MediaStream>;
    module?: Promise<void>;
  } = {},
) {
  let cleanup = () => {};
  t.after(() => cleanup());
  const calls = { media: 0, tickets: 0, tracksStopped: 0, contextsClosed: 0 };
  const events: VoiceEvent[] = [];
  const sockets: FakeSocket[] = [];
  const captures: Array<{
    port: { onmessage: ((event: { data: ArrayBuffer }) => void) | null };
  }> = [];
  const sources: Array<{
    onended: (() => void) | null;
    stop(): void;
    connect(): void;
    start(): void;
    buffer: unknown;
  }> = [];
  const track = {
    stop() {
      calls.tracksStopped++;
    },
  };
  const stream = { getTracks: () => [track] } as unknown as MediaStream;
  class FakeSocket {
    static OPEN = 1;
    readyState = 1;
    bufferedAmount = 0;
    onopen: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onmessage: ((message: { data: string }) => void) | null = null;
    sent: Array<{ type?: string; audio?: string }> = [];
    constructor() {
      sockets.push(this);
    }
    send(value: string) {
      this.sent.push(JSON.parse(value));
    }
    close() {
      this.readyState = 3;
    }
    emit(value: unknown) {
      this.onmessage?.({ data: JSON.stringify(value) });
    }
  }
  class FakeContext {
    currentTime = 0;
    destination = {};
    resume() {
      return options.resume ?? Promise.resolve();
    }
    close() {
      calls.contextsClosed++;
      return Promise.resolve();
    }
    audioWorklet = { addModule: () => options.module ?? Promise.resolve() };
    createMediaStreamSource() {
      return { connect: (node: unknown) => node, disconnect() {} };
    }
    createGain() {
      return { gain: { value: 1 }, connect() {}, disconnect() {} };
    }
    createAnalyser() {
      return {
        fftSize: 0,
        connect() {},
        disconnect() {},
        getFloatTimeDomainData() {},
      };
    }
    createBuffer(_channels: number, length: number, rate: number) {
      return {
        getChannelData: () => new Float32Array(length),
        duration: length / rate,
      };
    }
    createBufferSource() {
      const source = {
        onended: null as (() => void) | null,
        stop() {},
        connect() {},
        start() {},
        buffer: null as unknown,
      };
      sources.push(source);
      return source;
    }
  }
  const replace = (target: object, key: string, value: unknown) => {
    const old = Object.getOwnPropertyDescriptor(target, key);
    Object.defineProperty(target, key, { configurable: true, value });
    t.after(() => {
      if (old) Object.defineProperty(target, key, old);
      else Reflect.deleteProperty(target, key);
    });
  };
  replace(globalThis, "AudioContext", FakeContext);
  replace(
    globalThis,
    "AudioWorkletNode",
    class {
      port = {
        onmessage: null as ((event: { data: ArrayBuffer }) => void) | null,
        close() {},
      };
      constructor() {
        captures.push(this);
      }
      connect(node: unknown) {
        return node;
      }
      disconnect() {}
    },
  );
  replace(globalThis, "WebSocket", FakeSocket);
  replace(globalThis, "BroadcastChannel", undefined);
  replace(globalThis, "window", new EventTarget());
  replace(navigator, "mediaDevices", {
    getUserMedia() {
      calls.media++;
      return options.media ?? Promise.resolve(stream);
    },
  });
  const audio = new VoiceAudio((event) => events.push(event));
  cleanup = () => audio.close();
  const start = (mode: "text" | "voice" = "voice") =>
    audio.start(
      async () => {
        calls.tickets++;
        return "synthetic-ticket";
      },
      "en",
      "ws://fixture.invalid",
      { mode },
    );
  return { audio, start, calls, events, sockets, sources, stream, captures };
}

test("cancel during audio resume does not subsequently request a microphone", async (t) => {
  const resume = deferred<void>();
  const f = setup(t, { resume: resume.promise });
  const starting = f.start();
  f.audio.close();
  resume.resolve();
  await starting;
  assert.equal(f.calls.media, 0);
  assert.equal(f.calls.tickets, 0);
  assert.equal(f.sockets.length, 0);
});
test("late microphone permission releases tracks without making a ticket", async (t) => {
  const media = deferred<MediaStream>();
  const f = setup(t, { media: media.promise });
  const starting = f.start();
  await Promise.resolve();
  f.audio.close();
  media.resolve(f.stream);
  await starting;
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.calls.tickets, 0);
});
test("cancel while loading worklet prevents ticket and socket creation", async (t) => {
  const module = deferred<void>();
  const f = setup(t, { module: module.promise });
  const starting = f.start();
  await Promise.resolve();
  await Promise.resolve();
  f.audio.close();
  module.resolve();
  await starting;
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.calls.tickets, 0);
});
test("connection timeout stops tracks and detaches late socket handlers", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const f = setup(t);
  await f.start();
  const oldReady = f.sockets[0].onmessage;
  t.mock.timers.tick(10000);
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.sockets[0].readyState, 3);
  oldReady?.({ data: '{"type":"ready"}' });
  assert.equal(f.events.filter((e) => e.type === "ready").length, 0);
  assert.equal(
    f.events.filter((e) => e.code === "VOICE_CONNECT_TIMEOUT").length,
    1,
  );
});
test("ready clears connection timeout and malformed messages close cleanly", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const f = setup(t);
  await f.start();
  f.sockets[0].emit({ type: "ready" });
  t.mock.timers.tick(20000);
  assert.equal(f.calls.tracksStopped, 0);
  f.sockets[0].onmessage?.({ data: "not-json" });
  assert.equal(f.calls.tracksStopped, 1);
  assert.ok(f.events.some((e) => e.type === "error"));
});
test("odd-length PCM is reported as an error, never a silent stuck microphone", async (t) => {
  const f = setup(t);
  await f.start();
  f.sockets[0].emit({ type: "ready" });
  f.sockets[0].emit({ type: "audio", audio: "AQ==", sample_rate: 24000 });
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.sources.length, 0);
  assert.ok(f.events.some((e) => e.type === "error"));
});
test("provider completion waits for local playback drain; interrupt drops queued completion", async (t) => {
  const f = setup(t);
  await f.start();
  const s = f.sockets[0];
  s.emit({ type: "ready" });
  s.emit({ type: "audio", audio: "AAAAAA==", sample_rate: 24000 });
  s.emit({ type: "turn_complete" });
  s.emit({ type: "state", state: "listening" });
  assert.equal(
    f.events.filter(
      (e) => e.type === "turn_complete" || e.state === "listening",
    ).length,
    0,
  );
  f.sources[0].onended?.();
  assert.equal(f.events.filter((e) => e.type === "turn_complete").length, 1);
  assert.equal(s.sent.filter((e) => e.type === "playback_ended").length, 1);
  s.emit({ type: "audio", audio: "AAAAAA==", sample_rate: 24000 });
  s.emit({ type: "turn_complete" });
  f.audio.interrupt();
  assert.equal(f.sources[1].onended, null);
  assert.equal(f.events.filter((e) => e.type === "turn_complete").length, 1);
});

test("a fast provider can queue a complete meeting answer; excessive backlog fails explicitly", async (t) => {
  const f = setup(t);
  await f.start();
  const s = f.sockets[0];
  s.emit({ type: "ready" });
  const fiveSeconds = Buffer.alloc(24000 * 2 * 5).toString("base64");
  for (let i = 0; i < 4; i++)
    s.emit({ type: "audio", audio: fiveSeconds, sample_rate: 24000 });
  assert.equal(f.sources.length, 4);
  assert.equal(
    f.events.some((e) => e.type === "error"),
    false,
  );
  s.emit({ type: "audio", audio: fiveSeconds, sample_rate: 24000 });
  s.emit({ type: "audio", audio: fiveSeconds, sample_rate: 24000 });
  assert.ok(f.events.some((e) => e.code === "AUDIO_CONNECTION_SLOW"));
  assert.equal(f.calls.tracksStopped, 1);
  assert.ok(f.sources.every((source) => source.onended === null));
});

test("text connects and completes without any audio context, capture, or playback", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const f = setup(t);
  await f.start("text");
  const s = f.sockets[0];
  s.emit({ type: "ready", mode: "text" });
  await f.audio.sendText("下周有哪些会议？");
  assert.equal(f.calls.media, 0);
  assert.equal(f.calls.contextsClosed, 0);
  s.emit({ type: "turn_waiting", turn_id: 1, input_kind: "text" });
  s.emit({
    type: "transcript",
    role: "assistant",
    text: "下周没有会议",
    final: true,
  });
  s.emit({ type: "turn_complete", turn_id: 1, mode: "text" });
  t.mock.timers.tick(11000);
  assert.equal(
    f.events.some((e) => e.type === "error"),
    false,
  );
  assert.equal(f.events.filter((e) => e.type === "turn_complete").length, 1);
  assert.equal(
    s.sent.some((e) => e.type === "playback_ended"),
    false,
  );
});

test("text to voice and back reuses one socket and ticket, stopping microphone tracks", async (t) => {
  const f = setup(t);
  await f.start("text");
  const s = f.sockets[0];
  s.emit({ type: "ready", mode: "text" });
  const switching = f.audio.setMode("voice");
  for (let i = 0; i < 8; i++) await Promise.resolve();
  assert.equal(f.calls.media, 1);
  assert.ok(s.sent.some((e) => e.type === "mode"));
  s.emit({ type: "ready", mode: "voice" });
  await switching;
  const typing = f.audio.setMode("text");
  await Promise.resolve();
  assert.equal(f.calls.tracksStopped, 1);
  s.emit({ type: "ready", mode: "text" });
  await typing;
  await f.audio.sendText("把第二个改到周五");
  assert.equal(f.sockets.length, 1);
  assert.equal(f.calls.tickets, 1);
});

test("closing a text connection rejects pending submission and cannot send after ready", async (t) => {
  const f = setup(t);
  await f.start("text");
  const sending = f.audio.sendText("Do not send after close");
  f.audio.close();
  await assert.rejects(sending);
  f.sockets[0].emit({ type: "ready", mode: "text" });
  assert.equal(f.sockets[0].sent.length, 0);
  assert.equal(f.calls.media, 0);
});

test("text output mode never plays unexpected provider audio", async (t) => {
  const f = setup(t);
  await f.start("text");
  f.sockets[0].emit({ type: "ready", mode: "text" });
  f.sockets[0].emit({ type: "audio", audio: "AAAAAA==", sample_rate: 24000 });
  assert.ok(f.events.some((e) => e.code === "VOICE_OUTPUT_MODE_MISMATCH"));
  assert.equal(f.sources.length, 0);
  assert.equal(f.calls.media, 0);
});

test("speech captured while connecting is sent intact once ready", async (t) => {
  const f = setup(t);
  await f.start();
  const s = f.sockets[0];
  const pcm = new Uint8Array(1280).fill(42).buffer;
  f.captures[0].port.onmessage?.({ data: pcm });
  assert.equal(s.sent.filter((m) => m.type === "audio").length, 0);
  s.emit({ type: "ready", mode: "voice" });
  assert.deepEqual(
    s.sent.filter((m) => m.type === "audio").map((m) => m.audio),
    [Buffer.from(pcm).toString("base64")],
  );
});

test("pre-ready audio has a five-second bound and never uploads a truncated question", async (t) => {
  const f = setup(t);
  await f.start();
  const s = f.sockets[0];
  for (let i = 0; i < 126; i++)
    f.captures[0].port.onmessage?.({ data: new ArrayBuffer(1280) });
  assert.ok(f.events.some((e) => e.code === "VOICE_CONNECT_TIMEOUT"));
  assert.equal(s.sent.filter((m) => m.type === "audio").length, 0);
  assert.equal(f.calls.tracksStopped, 1);
});

test("network loss releases capture and old frames cannot pollute an explicit new connection", async (t) => {
  const f = setup(t);
  await f.start();
  const old = f.sockets[0];
  old.emit({ type: "ready" });
  old.emit({ type: "audio", audio: "AAAAAA==", sample_rate: 24000 });
  const late = old.onmessage;
  old.onclose?.();
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.sources[0].onended, null);
  assert.equal(f.calls.tickets, 1); // no automatic provider reconnect
  const nextEvents: VoiceEvent[] = [];
  const next = new VoiceAudio((event) => nextEvents.push(event));
  await next.start(
    async () => "explicit-next-ticket",
    "en",
    "ws://fixture.invalid",
    { mode: "text" },
  );
  late?.({
    data: JSON.stringify({
      type: "transcript",
      text: "OLD-ANSWER",
      role: "assistant",
    }),
  });
  assert.ok(!f.events.some((event) => event.text === "OLD-ANSWER"));
  f.sockets[1].emit({ type: "ready", mode: "text" });
  await next.sendText("New request");
  assert.ok(f.sockets[1].sent.some((event) => event.type === "text"));
  assert.ok(!nextEvents.some((event) => event.text === "OLD-ANSWER"));
  next.close();
});

test("selected task and conversation identifiers reach the text handshake without microphone access", async (t) => {
  const f = setup(t);
  await f.audio.start(
    async () => "synthetic-ticket",
    "en",
    "ws://fixture.invalid",
    {
      mode: "text",
      conversationId: "chat-for-task",
      taskId: "selected-task",
    },
  );
  f.sockets[0].onopen?.();
  assert.deepEqual(f.sockets[0].sent[0], {
    ticket: "synthetic-ticket",
    language: "en",
    mode: "text",
    conversation_id: "chat-for-task",
    task_id: "selected-task",
    prebuffer_ms: 5000,
  });
  assert.equal(f.calls.media, 0);
});

test("Live capture announces a new acoustic input only when the server advertises support", async (t) => {
  const f = setup(t);
  await f.start();
  f.sockets[0].onopen?.();
  f.sockets[0].emit({ type: "ready", continuous: true, input_markers: true });
  const frame = new Int16Array(800).fill(2500).buffer;
  f.captures[0].port.onmessage?.({ data: frame });
  f.captures[0].port.onmessage?.({ data: frame });
  assert.equal(
    f.sockets[0].sent.filter((x) => x.type === "input_started").length,
    1,
  );
  assert.equal(f.sockets[0].sent.filter((x) => x.type === "audio").length, 2);
});

test("older voice servers receive PCM without unsupported acoustic control events", async (t) => {
  const f = setup(t);
  await f.start();
  f.sockets[0].emit({ type: "ready", continuous: true });
  f.captures[0].port.onmessage?.({
    data: new Int16Array(800).fill(2500).buffer,
  });
  assert.ok(f.sockets[0].sent.every((x) => x.type !== "input_started"));
});

test("Live overlapping input does not discard speech already queued for playback", async (t) => {
  const f = setup(t);
  await f.start();
  f.sockets[0].emit({ type: "ready", continuous: true });
  f.sockets[0].emit({ type: "turn_waiting", turn_id: 1 });
  f.sockets[0].emit({
    type: "audio",
    turn_id: 1,
    audio: Buffer.from(new Int16Array(1200).fill(500).buffer).toString(
      "base64",
    ),
    sample_rate: 24000,
  });
  let stopped = 0;
  f.sources[0].stop = () => {
    stopped++;
  };
  f.sockets[0].emit({ type: "turn_waiting", turn_id: 2 });
  assert.equal(stopped, 0);
});

test("a detected wake is explicit in the voice handshake and never inferred for typed input", async (t) => {
  const f = setup(t);
  await f.audio.start(
    async () => "synthetic-ticket",
    "en",
    "ws://fixture.invalid",
    { mode: "voice", wakeTriggered: true },
  );
  f.sockets[0].onopen?.();
  assert.equal(
    (f.sockets[0].sent[0] as { wake_triggered?: boolean }).wake_triggered,
    true,
  );
});

test("wake handover reacquires authorized capture before audio resume and cancels without a model ticket", async (t) => {
  const resume = deferred<void>();
  const f = setup(t, { resume: resume.promise });
  const starting = f.audio.start(
    async () => {
      f.calls.tickets++;
      return "synthetic";
    },
    "en",
    "ws://fixture.invalid",
    { mode: "voice", wakeTriggered: true },
  );
  await Promise.resolve();
  assert.equal(f.calls.media, 1);
  assert.equal(f.calls.tickets, 0);
  f.audio.close();
  resume.resolve();
  await starting;
  assert.equal(f.calls.tracksStopped, 1);
  assert.equal(f.calls.tickets, 0);
});
