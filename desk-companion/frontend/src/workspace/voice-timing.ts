/** Monotonic capture / output-clock correlation. No PCM or transcript is retained. */
export type OutputClock = Pick<AudioContext, "currentTime" | "state"> & {
  outputLatency?: number;
  getOutputTimestamp?: () => AudioTimestamp;
};
export function renderedAt(clock: OutputClock, scheduled: number, now: number) {
  if (clock.state !== "running") return null;
  const stamp = clock.getOutputTimestamp?.();
  if (
    stamp &&
    Number.isFinite(stamp.contextTime) &&
    Number.isFinite(stamp.performanceTime) &&
    stamp.contextTime! > 0 &&
    stamp.performanceTime! > 0 &&
    Math.abs(stamp.performanceTime! - now) < 5000
  ) {
    if (stamp.contextTime! < scheduled) return null;
    return {
      at: stamp.performanceTime! + (scheduled - stamp.contextTime!) * 1000,
      source: "output_timestamp" as const,
    };
  }
  const latency = Number.isFinite(clock.outputLatency)
    ? clock.outputLatency!
    : 0;
  if (clock.currentTime - latency < scheduled) return null;
  return {
    at: now + (scheduled + latency - clock.currentTime) * 1000,
    source: "audio_context_estimate" as const,
  };
}

export class CaptureTimeline {
  private sentMs = 0;
  voiced = false;
  lastVoiceStreamMs = 0;
  private lastVoice = -Infinity;
  private active = false;
  private voicedMs = 0;
  private ended = false;
  private segments: Array<{ end: number; voiceAt: number }> = [];
  observe(pcm: ArrayBuffer, endAt: number) {
    const samples = new DataView(pcm);
    const duration = pcm.byteLength / 32;
    let voiceIndex = -1;
    let energy = 0;
    for (let i = 0; i < pcm.byteLength / 2; i++) {
      const value = samples.getInt16(i * 2, true);
      energy += value * value;
      if (Math.abs(value) >= 328) voiceIndex = i;
    }
    if (Math.sqrt(energy / (pcm.byteLength / 2)) < 328) voiceIndex = -1;
    this.sentMs += duration;
    this.voiced = voiceIndex >= 0;
    if (voiceIndex >= 0) {
      this.lastVoiceStreamMs = this.sentMs - duration + (voiceIndex + 1) / 16;
      this.lastVoice = endAt - duration + (voiceIndex + 1) / 16;
      this.voicedMs += duration;
      this.active = this.voicedMs >= 120;
      this.ended = false;
    }
    this.segments.push({ end: this.sentMs, voiceAt: this.lastVoice });
    if (this.segments.length > 1500) this.segments.shift();
    const boundary =
      this.active && !this.ended && endAt - this.lastVoice >= 400;
    if (boundary) {
      this.ended = true;
      this.active = false;
      this.voicedMs = 0;
    } else if (!this.active && endAt - this.lastVoice >= 400) this.voicedMs = 0;
    return boundary;
  }
  endpoint(providerEndMs: number | undefined, fallback: number) {
    const segment =
      providerEndMs === undefined
        ? this.segments.at(-1)
        : this.segments.find((s) => s.end >= providerEndMs);
    const voiceAt = segment?.voiceAt;
    if (
      voiceAt !== undefined &&
      Number.isFinite(voiceAt) &&
      voiceAt <= fallback &&
      fallback - voiceAt < 15000
    )
      return { at: voiceAt, source: "capture_energy" as const };
    return { at: fallback, source: "provider_event" as const };
  }
}

export function hasCaptureSpeech(pcm: ArrayBuffer): boolean {
  if (pcm.byteLength < 2 || pcm.byteLength % 2) return false;
  const values = new DataView(pcm);
  let energy = 0;
  for (let i = 0; i < pcm.byteLength; i += 2) {
    const value = values.getInt16(i, true);
    energy += value * value;
  }
  return Math.sqrt(energy / (pcm.byteLength / 2)) >= 328;
}

export interface PendingPlaybackMark {
  turn: number;
  audio: number;
  at: number;
  afterTool: boolean;
}
export interface TurnMeasurement {
  turn_id: number;
  first_text_ms?: number | null;
  first_played_ms?: number | null;
  post_tool_played_ms?: number | null;
  timing_source?: string | null;
  endpoint_source?: string | null;
  semantic_verified?: boolean;
  response_started?: boolean;
}
