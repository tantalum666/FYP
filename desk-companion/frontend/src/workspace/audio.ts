import { encodeVoiceImage } from "./vision.ts";
import { OutputMeter } from "../companion/output.ts";

export interface VoiceEvent {
  type: string;
  state?: string;
  code?: string;
  text?: string;
  role?: string;
  audio?: string;
  sample_rate?: number;
  final?: boolean;
  active?: boolean;
  count?: number;
}

export class VoiceAudio {
  private context: AudioContext | null = null;
  private meter: OutputMeter | null = null;
  private stream: MediaStream | null = null;
  private socket: WebSocket | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private nextTime = 0;
  private ready = false;
  private stopped = false;
  private audioSent = false;
  private visionActive = false;
  private visionGeneration = 0;
  private visionStream: MediaStream | null = null;
  private visionVideo: HTMLVideoElement | null = null;
  private visionTimer: ReturnType<typeof setTimeout> | null = null;
  private lastImage = 0;
  private onEvent: (event: VoiceEvent) => void;
  constructor(onEvent: (event: VoiceEvent) => void) {
    this.onEvent = onEvent;
  }
  async start(
    getTicket: () => Promise<string>,
    language: string,
    endpoint: string,
  ) {
    try {
      this.context = new AudioContext();
      await this.context.resume();
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      if (this.stopped) {
        this.close();
        return;
      }
      await this.context.audioWorklet.addModule("/audio-capture.js");
      const capture = new AudioWorkletNode(this.context, "desk-capture");
      const input = this.context.createMediaStreamSource(this.stream);
      const mute = this.context.createGain();
      mute.gain.value = 0;
      input.connect(capture).connect(mute).connect(this.context.destination);
      const ticket = await getTicket();
      if (this.stopped) {
        this.close();
        return;
      }
      const socket = new WebSocket(endpoint);
      this.socket = socket;
      socket.onopen = () => socket.send(JSON.stringify({ ticket, language }));
      capture.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (!this.ready || socket.readyState !== WebSocket.OPEN) return;
        if (socket.bufferedAmount > 64000) {
          this.onEvent({ type: "error", code: "AUDIO_CONNECTION_SLOW" });
          this.close();
          return;
        }
        let binary = "";
        for (const value of new Uint8Array(event.data))
          binary += String.fromCharCode(value);
        socket.send(JSON.stringify({ type: "audio", audio: btoa(binary) }));
        this.audioSent = true;
      };
      socket.onmessage = (raw) => {
        const event = JSON.parse(raw.data) as VoiceEvent;
        if (event.type === "ready") this.ready = true;
        if (event.type === "interrupted") this.clearPlayback();
        if (event.type === "audio" && event.audio)
          this.play(event.audio, event.sample_rate ?? 24000);
        this.onEvent(event);
        if (event.type === "error" || event.type === "ended") this.close();
      };
      socket.onerror = () => {
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
    if (!context) return;
    const raw = atob(encoded),
      bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    const pcm = new DataView(bytes.buffer),
      length = bytes.length / 2;
    if (rate !== 24000 || length > 240000) {
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
    this.meter ??= new OutputMeter(context);
    source.connect(this.meter.input);
    this.meter.start();
    this.sources.add(source);
    source.onended = () => {
      this.sources.delete(source);
      if (!this.sources.size) this.meter?.reset();
      if (!this.sources.size && this.socket?.readyState === WebSocket.OPEN)
        this.socket.send(JSON.stringify({ type: "playback_ended" }));
    };
    source.start(this.nextTime);
    this.nextTime += buffer.duration;
  }
  interrupt() {
    this.clearPlayback();
    if (this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(JSON.stringify({ type: "interrupt" }));
  }
  private visionReady() {
    return (
      !this.stopped &&
      this.ready &&
      this.audioSent &&
      this.socket?.readyState === WebSocket.OPEN
    );
  }
  private sendImage(image: string) {
    if (!this.visionReady() || !this.socket)
      throw new Error("VOICE_VISION_NOT_READY");
    if (performance.now() - this.lastImage < 1000 && this.lastImage !== 0)
      throw new Error("VOICE_IMAGE_RATE_LIMIT");
    if (this.socket.bufferedAmount > 64000)
      throw new Error("AUDIO_CONNECTION_SLOW");
    if (!this.visionActive) {
      this.socket.send(JSON.stringify({ type: "vision_start" }));
      this.visionActive = true;
    }
    this.socket.send(JSON.stringify({ type: "image", image }));
    this.lastImage = performance.now();
  }
  async shareImage(file: File) {
    if (!this.visionReady()) throw new Error("VOICE_VISION_NOT_READY");
    if (
      !/^image\/(jpeg|png|webp)$/.test(file.type) ||
      file.size > 4 * 1024 * 1024
    )
      throw new Error("INVALID_VOICE_IMAGE");
    this.stopVision();
    const generation = this.visionGeneration;
    const image = await createImageBitmap(file);
    try {
      if (generation !== this.visionGeneration || !this.visionReady()) return;
      this.sendImage(encodeVoiceImage(image, image.width, image.height));
      // A still image is sent once. Previously sent content stays in session context.
      this.stopVision();
    } finally {
      image.close();
    }
  }
  async shareScreen() {
    if (!this.visionReady() || !navigator.mediaDevices?.getDisplayMedia)
      throw new Error("VOICE_VISION_NOT_READY");
    this.stopVision();
    const generation = this.visionGeneration;
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: { ideal: 1, max: 1 } },
      audio: false,
    });
    if (generation !== this.visionGeneration || !this.visionReady()) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    this.visionStream = stream;
    const video = document.createElement("video");
    this.visionVideo = video;
    video.muted = true;
    video.playsInline = true;
    video.srcObject = stream;
    try {
      await video.play();
    } catch (error) {
      this.stopVision();
      throw error;
    }
    if (generation !== this.visionGeneration || !this.visionReady()) {
      this.stopVision();
      return;
    }
    for (const track of stream.getTracks())
      track.onended = () => this.stopVision();
    this.onEvent({ type: "vision", active: true });
    const frame = () => {
      if (generation !== this.visionGeneration || !this.visionReady()) return;
      if (video.readyState >= 2 && video.videoWidth && video.videoHeight) {
        try {
          this.sendImage(
            encodeVoiceImage(video, video.videoWidth, video.videoHeight),
          );
        } catch (error) {
          if (
            !(error instanceof Error) ||
            error.message !== "VOICE_IMAGE_RATE_LIMIT"
          ) {
            this.onEvent({
              type: "vision_error",
              code:
                error instanceof Error
                  ? error.message
                  : "VOICE_IMAGE_UNAVAILABLE",
            });
            this.stopVision();
            return;
          }
        }
      }
      this.visionTimer = setTimeout(frame, 1000);
    };
    frame();
  }
  stopVision() {
    this.visionGeneration++;
    if (this.visionTimer) clearTimeout(this.visionTimer);
    this.visionTimer = null;
    this.visionStream?.getTracks().forEach((track) => {
      track.onended = null;
      track.stop();
    });
    this.visionStream = null;
    if (this.visionVideo) {
      this.visionVideo.pause();
      this.visionVideo.srcObject = null;
      this.visionVideo = null;
    }
    if (this.visionActive && this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(JSON.stringify({ type: "vision_stop" }));
    this.visionActive = false;
    this.onEvent({ type: "vision", active: false });
  }
  private clearPlayback() {
    this.meter?.reset();
    for (const source of this.sources) {
      source.onended = null;
      try {
        source.stop();
      } catch {
        /* already ended */
      }
    }
    this.sources.clear();
    this.nextTime = 0;
  }
  close() {
    this.stopped = true;
    this.ready = false;
    this.stopVision();
    this.clearPlayback();
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.socket) {
      const socket = this.socket;
      this.socket = null;
      socket.onclose = null;
      socket.close();
    }
    this.meter?.close();
    this.meter = null;
    if (this.context) {
      void this.context.close();
      this.context = null;
    }
  }
}
