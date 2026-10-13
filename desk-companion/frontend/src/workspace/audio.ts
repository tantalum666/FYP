import { PlaybackMeter } from "../avatar/playback";

export interface VoiceEvent {
  type: string;
  state?: string;
  code?: string;
  text?: string;
  role?: string;
  audio?: string;
  sample_rate?: number;
  final?: boolean;
  suppressed?: boolean;
}

export class VoiceAudio {
  private context: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private socket: WebSocket | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private meter: PlaybackMeter | null = null;
  private nextTime = 0;
  private ready = false;
  private stopped = false;
  private speechMuted = false;
  constructor(
    private onEvent: (event: VoiceEvent) => void,
    private isCurrent: () => boolean = () => true,
  ) {}
  private current() {
    if (this.stopped) return false;
    if (!this.isCurrent()) {
      this.close();
      return false;
    }
    return true;
  }
  async start(
    getTicket: () => Promise<string>,
    language: string,
    endpoint: string,
  ) {
    try {
      if (!this.current()) return;
      this.context = new AudioContext();
      await this.context.resume();
      if (!this.current()) return;
      this.meter = new PlaybackMeter(this.context);
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      if (!this.current()) {
        this.close();
        return;
      }
      await this.context.audioWorklet.addModule("/audio-capture.js");
      if (!this.current() || !this.context) return;
      const capture = new AudioWorkletNode(this.context, "desk-capture");
      const input = this.context.createMediaStreamSource(this.stream);
      const mute = this.context.createGain();
      mute.gain.value = 0;
      input.connect(capture).connect(mute).connect(this.context.destination);
      const ticket = await getTicket();
      if (!this.current()) {
        this.close();
        return;
      }
      const socket = new WebSocket(endpoint);
      this.socket = socket;
      socket.onopen = () => {
        if (this.current() && this.socket === socket)
          socket.send(JSON.stringify({ ticket, language }));
      };
      capture.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (
          !this.current() ||
          !this.ready ||
          this.socket !== socket ||
          socket.readyState !== WebSocket.OPEN
        )
          return;
        if (socket.bufferedAmount > 64000) {
          this.onEvent({ type: "error", code: "AUDIO_CONNECTION_SLOW" });
          this.close();
          return;
        }
        let binary = "";
        for (const value of new Uint8Array(event.data))
          binary += String.fromCharCode(value);
        socket.send(JSON.stringify({ type: "audio", audio: btoa(binary) }));
      };
      socket.onmessage = (raw) => {
        if (!this.current() || this.socket !== socket) return;
        let event: VoiceEvent;
        try {
          event = JSON.parse(raw.data) as VoiceEvent;
        } catch {
          this.onEvent({ type: "error", code: "VOICE_EVENT_INVALID" });
          this.close();
          return;
        }
        if (!event || typeof event !== "object") return;
        if (event.type === "ready") this.ready = true;
        // Provider barge-in (including Qwen speech_started) clears queued old
        // output, but only an explicit owner Stop speaking latches mute.
        if (event.type === "interrupted") this.clearPlayback();
        if (event.type === "audio" && event.audio) {
          if (this.speechMuted) event.suppressed = true;
          else this.play(event.audio, event.sample_rate ?? 24000);
          if (!this.current()) return;
        }
        this.onEvent(event);
        if (event.type === "error" || event.type === "ended") this.close();
      };
      socket.onerror = () => {
        if (!this.current() || this.socket !== socket) return;
        this.onEvent({ type: "error", code: "VOICE_CONNECTION_FAILED" });
        this.close();
      };
      socket.onclose = () => {
        this.close();
        this.onEvent({ type: "closed" });
      };
    } catch (error) {
      this.close();
      throw error;
    }
  }
  private play(encoded: string, rate: number) {
    const context = this.context;
    if (!this.current() || !context || this.speechMuted) return;
    let bytes: Uint8Array;
    try {
      if (typeof encoded !== "string" || encoded.length > 640000)
        throw new Error("invalid PCM");
      const raw = atob(encoded);
      bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    } catch {
      this.onEvent({ type: "error", code: "VOICE_AUDIO_INVALID" });
      this.close();
      return;
    }
    const pcm = new DataView(bytes.buffer),
      length = bytes.length / 2;
    if (
      rate !== 24000 ||
      !Number.isInteger(length) ||
      length < 1 ||
      length > 240000
    ) {
      this.onEvent({ type: "error", code: "VOICE_AUDIO_INVALID" });
      this.close();
      return;
    }
    const buffer = context.createBuffer(1, length, rate),
      values = buffer.getChannelData(0);
    for (let i = 0; i < length; i++)
      values[i] = pcm.getInt16(i * 2, true) / 32768;
    this.nextTime = Math.max(context.currentTime + 0.02, this.nextTime);
    if (this.nextTime - context.currentTime > 8) {
      this.onEvent({ type: "error", code: "AUDIO_CONNECTION_SLOW" });
      this.close();
      return;
    }
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.meter?.input ?? context.destination);
    this.meter?.start();
    this.sources.add(source);
    source.onended = () => {
      this.sources.delete(source);
      source.disconnect();
      if (!this.sources.size) this.meter?.reset();
      if (
        this.current() &&
        !this.sources.size &&
        this.socket?.readyState === WebSocket.OPEN
      )
        this.socket.send(JSON.stringify({ type: "playback_ended" }));
    };
    source.start(this.nextTime);
    this.nextTime += buffer.duration;
  }
  interrupt() {
    if (!this.current()) return;
    this.speechMuted = true;
    this.clearPlayback();
    this.onEvent({ type: "speech_muted" });
    if (this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(JSON.stringify({ type: "interrupt" }));
  }
  hearAgain() {
    if (!this.current()) return;
    this.speechMuted = false;
    this.onEvent({ type: "speech_resumed" });
  }
  private clearPlayback() {
    for (const source of this.sources) {
      source.onended = null;
      try {
        source.stop();
      } catch {
        /* already ended */
      }
      source.disconnect();
    }
    this.sources.clear();
    this.nextTime = 0;
    this.meter?.reset();
  }
  close() {
    this.stopped = true;
    this.ready = false;
    this.clearPlayback();
    this.meter?.close();
    this.meter = null;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.socket) {
      const socket = this.socket;
      this.socket = null;
      socket.onclose = null;
      socket.onmessage = null;
      socket.onopen = null;
      socket.onerror = null;
      socket.close();
    }
    if (this.context) {
      void this.context.close();
      this.context = null;
    }
  }
}
