import assert from "node:assert/strict";
import test from "node:test";
import { WakeAudio } from "../src/workspace/wake/WakeAudio.ts";
function fixtures(pending?: Promise<MediaStream>) {
  const prior = {
    context: globalThis.AudioContext,
    worklet: globalThis.AudioWorkletNode,
    socket: globalThis.WebSocket,
    media: navigator.mediaDevices,
  };
  let stopped = 0,
    closedContext = 0,
    tickets = 0;
  const stream = {
    getTracks: () => [{ stop: () => stopped++ }],
  } as unknown as MediaStream;
  let worklet: any;
  const sockets: any[] = [];
  class Context {
    destination = {};
    audioWorklet = {
      addModule: async (path: string) =>
        assert.equal(path, "/audio-capture.js"),
    };
    resume() {
      return Promise.resolve();
    }
    close() {
      closedContext++;
      return Promise.resolve();
    }
    createMediaStreamSource() {
      return { connect: (x: any) => x, disconnect() {} };
    }
    createGain() {
      return { gain: { value: 1 }, connect: (x: any) => x, disconnect() {} };
    }
  }
  class Worklet {
    port: any = { onmessage: null, close() {} };
    connect(x: any) {
      return x;
    }
    disconnect() {}
    constructor() {
      worklet = this;
    }
  }
  class Socket {
    static OPEN = 1;
    readyState = 1;
    bufferedAmount = 0;
    sent: any[] = [];
    onopen: any;
    onmessage: any;
    onerror: any;
    onclose: any;
    url: string;
    constructor(url: string) {
      this.url = url;
      sockets.push(this);
    }
    send(value: any) {
      this.sent.push(value);
    }
    close() {
      this.readyState = 3;
    }
  }
  Object.defineProperty(globalThis, "AudioContext", {
    configurable: true,
    value: Context,
  });
  Object.defineProperty(globalThis, "AudioWorkletNode", {
    configurable: true,
    value: Worklet,
  });
  Object.defineProperty(globalThis, "WebSocket", {
    configurable: true,
    value: Socket,
  });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: () => pending ?? Promise.resolve(stream) },
  });
  return {
    stream,
    sockets,
    worklet: () => worklet,
    counts: () => ({ stopped, closedContext, tickets }),
    ticket: async () => {
      tickets++;
      return "local-ticket";
    },
    restore: () => {
      Object.defineProperty(globalThis, "AudioContext", {
        configurable: true,
        value: prior.context,
      });
      Object.defineProperty(globalThis, "AudioWorkletNode", {
        configurable: true,
        value: prior.worklet,
      });
      Object.defineProperty(globalThis, "WebSocket", {
        configurable: true,
        value: prior.socket,
      });
      Object.defineProperty(navigator, "mediaDevices", {
        configurable: true,
        value: prior.media,
      });
    },
  };
}
test("wake channel sends no PCM until ready, and stops capture before a single wake callback", async () => {
  const f = fixtures(),
    events: any[] = [];
  const wake = new WakeAudio((event) =>
    events.push({ event, stopped: f.counts().stopped }),
  );
  try {
    await wake.start(f.ticket, "ws://127.0.0.1:8861/api/wake/ws");
    const ws = f.sockets[0];
    ws.onopen();
    const callback = ws.onmessage;
    f.worklet().port.onmessage({ data: { pcm: new ArrayBuffer(1280) } });
    assert.equal(ws.sent.length, 1);
    assert.equal(JSON.parse(ws.sent[0]).ticket, "local-ticket");
    ws.onmessage({ data: JSON.stringify({ type: "ready" }) });
    f.worklet().port.onmessage({ data: { pcm: new ArrayBuffer(1280) } });
    assert.ok(ws.sent[1] instanceof ArrayBuffer);
    callback({ data: JSON.stringify({ type: "wake" }) });
    callback({ data: JSON.stringify({ type: "wake" }) });
    assert.equal(events.filter((x) => x.event.type === "wake").length, 1);
    assert.equal(events.at(-1).stopped, 1);
    assert.equal(ws.readyState, 3);
    assert.equal(f.counts().closedContext, 1);
  } finally {
    wake.stop();
    f.restore();
  }
});
test("closing a pending wake permission request never obtains a ticket or reconnects", async () => {
  let resolve!: (s: MediaStream) => void;
  const pending = new Promise<MediaStream>((r) => (resolve = r));
  const f = fixtures(pending),
    events: any[] = [];
  const wake = new WakeAudio((e) => events.push(e));
  try {
    const starting = wake.start(f.ticket, "ws://127.0.0.1:8861/api/wake/ws");
    await Promise.resolve();
    wake.stop();
    resolve(f.stream);
    await starting;
    assert.deepEqual(f.counts(), { stopped: 1, closedContext: 1, tickets: 0 });
    assert.equal(f.sockets.length, 0);
    assert.deepEqual(events, []);
  } finally {
    wake.stop();
    f.restore();
  }
});
test("unexpected local disconnect releases capture and reports an error without retry", async () => {
  const f = fixtures(),
    events: any[] = [];
  const wake = new WakeAudio((e) => events.push(e));
  try {
    await wake.start(f.ticket, "ws://127.0.0.1:8861/api/wake/ws");
    f.sockets[0].onclose();
    assert.deepEqual(events, [{ type: "error" }]);
    assert.equal(f.counts().stopped, 1);
    assert.equal(f.sockets.length, 1);
  } finally {
    wake.stop();
    f.restore();
  }
});
