import { rmsLevel } from "./model.ts";
import type { PlaybackSample } from "./model.ts";

const CHANNEL = "desk.avatar.playback.v1";
const EVENT = "desk:avatar-playback";

export function subscribePlayback(receive: (sample: PlaybackSample) => void) {
  const accept = (sample: unknown) => {
    if (typeof sample !== "object" || sample === null) return;
    const s = sample as PlaybackSample;
    if (
      typeof s.level === "number" &&
      typeof s.at === "number" &&
      Number.isFinite(s.level) &&
      Number.isFinite(s.at)
    )
      receive({ level: s.level, at: s.at });
  };
  const local = (event: Event) => accept((event as CustomEvent).detail);
  window.addEventListener(EVENT, local);
  const channel =
    typeof BroadcastChannel === "undefined"
      ? null
      : new BroadcastChannel(CHANNEL);
  if (channel) channel.onmessage = (event) => accept(event.data);
  return () => {
    window.removeEventListener(EVENT, local);
    channel?.close();
  };
}

/** Measures only assistant output, after scheduling; microphone data never enters this bridge. */
export class PlaybackMeter {
  readonly input: AnalyserNode;
  private timer: ReturnType<typeof setInterval> | null = null;
  private channel: BroadcastChannel | null;
  private values = new Float32Array(512);
  private closed = false;
  private broadcast: boolean;
  constructor(
    context: AudioContext,
    receive?: (sample: PlaybackSample) => void,
    broadcast = true,
  ) {
    this.receive = receive;
    this.broadcast = broadcast;
    this.input = context.createAnalyser();
    this.input.fftSize = 512;
    this.input.connect(context.destination);
    this.channel =
      broadcast && typeof BroadcastChannel !== "undefined"
        ? new BroadcastChannel(CHANNEL)
        : null;
  }
  private receive?: (sample: PlaybackSample) => void;
  private emit(level: number) {
    const sample = { level, at: Date.now() };
    this.receive?.(sample);
    // Preview audio stays local to its component. Live output carries two numbers
    // between tabs on this origin, never PCM, text, credentials or server writes.
    if (this.broadcast) {
      window.dispatchEvent(new CustomEvent(EVENT, { detail: sample }));
      this.channel?.postMessage(sample);
    }
  }
  start() {
    if (this.closed || this.timer) return;
    this.timer = setInterval(() => {
      this.input.getFloatTimeDomainData(this.values);
      this.emit(rmsLevel(this.values));
    }, 40);
  }
  reset() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.emit(0);
  }
  close() {
    if (this.closed) return;
    this.reset();
    this.closed = true;
    this.input.disconnect();
    this.channel?.close();
    this.channel = null;
  }
}

/** A short synthetic vowel for checking output-driven mouth motion, without a provider or microphone. */
export async function previewVoice(
  receive: (sample: PlaybackSample) => void,
  ended: () => void,
) {
  const context = new AudioContext();
  await context.resume();
  const meter = new PlaybackMeter(context, receive, false);
  const duration = 2.4,
    buffer = context.createBuffer(
      1,
      Math.floor(context.sampleRate * duration),
      context.sampleRate,
    );
  const values = buffer.getChannelData(0);
  for (let i = 0; i < values.length; i++) {
    const t = i / context.sampleRate;
    const envelope =
      Math.max(0, Math.sin(t * Math.PI * 3.1)) ** 2 *
      Math.min(1, t * 15, (duration - t) * 10);
    values[i] =
      envelope *
      (0.13 * Math.sin(t * 2 * Math.PI * 180) +
        0.055 * Math.sin(t * 2 * Math.PI * 720) +
        0.025 * Math.sin(t * 2 * Math.PI * 1080));
  }
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(meter.input);
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    source.onended = null;
    try {
      source.stop();
    } catch {
      /* already ended */
    }
    source.disconnect();
    meter.close();
    void context.close();
    ended();
  };
  source.onended = stop;
  meter.start();
  source.start();
  return stop;
}
