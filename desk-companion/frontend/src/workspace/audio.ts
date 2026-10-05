export interface VoiceEvent {
  type: string;
  state?: string;
  code?: string;
  text?: string;
  role?: string;
  audio?: string;
  sample_rate?: number;
  final?: boolean;
}

export class VoiceAudio {
  private context: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private socket: WebSocket | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private nextTime = 0;
  private ready = false;
  private stopped = false;
  constructor(private onEvent: (event: VoiceEvent) => void) {}
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
    source.connect(context.destination);
    this.sources.add(source);
    source.onended = () => {
      this.sources.delete(source);
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
  private clearPlayback() {
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
    this.clearPlayback();
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.socket) {
      const socket = this.socket;
      this.socket = null;
      socket.onclose = null;
      socket.close();
    }
    if (this.context) {
      void this.context.close();
      this.context = null;
    }
  }
}
