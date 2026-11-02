import { LocalCapture } from "../media/localCapture.ts";

type WakeEvent = { type: "ready" | "wake" | "error" };
/** Microphone PCM goes only to the connected desk's local keyword detector. */
export class WakeAudio {
  private capture = new LocalCapture();
  private context: AudioContext | null = null;
  private input: MediaStreamAudioSourceNode | null = null;
  private node: AudioWorkletNode | null = null;
  private mute: GainNode | null = null;
  private socket: WebSocket | null = null;
  private stopped = false;
  private started = false;
  private ready = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private emit: (event: WakeEvent) => void;
  constructor(emit: (event: WakeEvent) => void) {
    this.emit = emit;
  }
  async start(ticket: () => Promise<string>, endpoint: string) {
    if (this.started || this.stopped) return;
    this.started = true;
    try {
      const context = new AudioContext();
      this.context = context;
      this.timer = setTimeout(() => this.fail(), 5000);
      await context.resume();
      if (this.stopped) return;
      if (this.timer) clearTimeout(this.timer);
      this.timer = null;
      const stream = await this.capture.start({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      if (!stream || this.stopped) return;
      await context.audioWorklet.addModule("/audio-capture.js");
      if (this.stopped) return;
      this.node = new AudioWorkletNode(context, "desk-capture");
      this.input = context.createMediaStreamSource(stream);
      this.mute = context.createGain();
      this.mute.gain.value = 0;
      this.input
        .connect(this.node)
        .connect(this.mute)
        .connect(context.destination);
      const value = await ticket();
      if (this.stopped) return;
      const socket = new WebSocket(endpoint);
      this.socket = socket;
      this.timer = setTimeout(() => this.fail(), 15000);
      socket.onopen = () => {
        if (!this.stopped) socket.send(JSON.stringify({ ticket: value }));
      };
      socket.onmessage = (message) => {
        if (this.stopped) return;
        try {
          const event = JSON.parse(message.data);
          if (event.type === "ready") {
            this.ready = true;
            if (this.timer) clearTimeout(this.timer);
            this.timer = null;
            this.emit({ type: "ready" });
          } else if (event.type === "wake" && this.ready) {
            this.stop();
            this.emit({ type: "wake" });
          } else if (event.type === "error") this.fail();
        } catch {
          this.fail();
        }
      };
      socket.onerror = () => this.fail();
      socket.onclose = () => {
        if (!this.stopped) this.fail();
      };
      this.node.port.onmessage = (
        event: MessageEvent<ArrayBuffer | { pcm: ArrayBuffer }>,
      ) => {
        if (this.stopped || !this.ready || socket.readyState !== WebSocket.OPEN)
          return;
        if (socket.bufferedAmount > 64000) {
          this.fail();
          return;
        }
        socket.send(
          event.data instanceof ArrayBuffer ? event.data : event.data.pcm,
        );
      };
    } catch {
      if (!this.stopped) this.fail();
    }
  }
  private fail() {
    if (this.stopped) return;
    this.stop();
    this.emit({ type: "error" });
  }
  stop() {
    if (this.stopped) return;
    this.stopped = true;
    this.ready = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.capture.stop();
    this.input?.disconnect();
    this.mute?.disconnect();
    if (this.node) {
      this.node.port.onmessage = null;
      this.node.port.close();
      this.node.disconnect();
    }
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
    }
    void this.context?.close().catch(() => {});
    this.input = null;
    this.mute = null;
    this.node = null;
    this.socket = null;
    this.context = null;
  }
}
