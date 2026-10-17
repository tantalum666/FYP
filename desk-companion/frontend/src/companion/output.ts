export interface PlaybackSample {
  level: number;
  at: number;
}
export function mouthLevel(sample: PlaybackSample, now: number) {
  return Number.isFinite(sample.level) &&
    Number.isFinite(sample.at) &&
    now - sample.at >= 0 &&
    now - sample.at < 300
    ? Math.max(0, Math.min(1, sample.level * 7))
    : 0;
}
const EVENT = "desk:avatar-playback";
const CHANNEL = "desk.avatar.playback.v1";
export function subscribePlayback(receive: (sample: PlaybackSample) => void) {
  const accept = (value: unknown) => {
    if (!value || typeof value !== "object") return;
    const s = value as PlaybackSample;
    if (
      typeof s.level === "number" &&
      typeof s.at === "number" &&
      Number.isFinite(s.level) &&
      Number.isFinite(s.at)
    )
      receive({ level: s.level, at: s.at });
  };
  const local = (e: Event) => accept((e as CustomEvent).detail);
  window.addEventListener(EVENT, local);
  const channel =
    typeof BroadcastChannel === "undefined"
      ? null
      : new BroadcastChannel(CHANNEL);
  if (channel) channel.onmessage = (e) => accept(e.data);
  return () => {
    window.removeEventListener(EVENT, local);
    channel?.close();
  };
}
/** Only measures scheduled speaker output. Never connects to microphone input. */
export class OutputMeter {
  readonly input: AnalyserNode;
  private values = new Float32Array(512);
  private timer: ReturnType<typeof setInterval> | null = null;
  private channel =
    typeof BroadcastChannel === "undefined"
      ? null
      : new BroadcastChannel(CHANNEL);
  constructor(context: AudioContext) {
    this.input = context.createAnalyser();
    this.input.fftSize = 512;
    this.input.connect(context.destination);
  }
  private emit(level: number) {
    const sample = { level, at: Date.now() };
    window.dispatchEvent(new CustomEvent(EVENT, { detail: sample }));
    this.channel?.postMessage(sample);
  }
  start() {
    if (this.timer) return;
    this.timer = setInterval(() => {
      this.input.getFloatTimeDomainData(this.values);
      let sum = 0;
      for (const n of this.values) sum += n * n;
      this.emit(Math.sqrt(sum / this.values.length));
    }, 40);
  }
  reset() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.emit(0);
  }
  close() {
    this.reset();
    this.input.disconnect();
    this.channel?.close();
    this.channel = null;
  }
}
