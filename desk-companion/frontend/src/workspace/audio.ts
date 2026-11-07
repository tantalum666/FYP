import { encodeVoiceImage } from "./vision.ts";
import { microphoneConstraints } from "./media/microphone.ts";
import { OutputMeter } from "../companion/output.ts";
import {
  CaptureTimeline,
  renderedAt,
  hasCaptureSpeech,
  type PendingPlaybackMark,
  type TurnMeasurement,
} from "./voice-timing.ts";

export interface VoiceEvent extends Partial<TurnMeasurement> {
  caption_group?: number;
  start_ms?: number;
  end_ms?: number;
  continuous?: boolean;
  input_markers?: boolean;
  mode?: "text" | "voice";
  conversation_id?: string;
  input_kind?: "text";
  reason?: string;
  audio_id?: number;
  after_tool?: boolean;
  input_end_ms?: number;
  timeout_ms?: number;
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
  private captureTimeline = new CaptureTimeline();
  private turn: {
    id: number;
    end: number;
    endpoint: string;
    first: boolean;
    postTool: boolean;
    qualified: boolean;
  } | null = null;
  private marks: PendingPlaybackMark[] = [];
  private markTimer: ReturnType<typeof setInterval> | null = null;
  private turnTimer: ReturnType<typeof setTimeout> | null = null;
  private completedTurnId: number | undefined;
  private ready = false;
  private continuous = false;
  private inputMarkers = false;
  private started = false;
  private capture: AudioWorkletNode | null = null;
  private inputNode: MediaStreamAudioSourceNode | null = null;
  private muteNode: GainNode | null = null;
  private connectTimer: ReturnType<typeof setTimeout> | null = null;
  private completedTurn = false;
  private stopped = false;
  private audioSent = false;
  private mode: "text" | "voice" = "voice";
  private captureGeneration = 0;
  private pendingCapture: Array<{ pcm: ArrayBuffer; endAt: number }> = [];
  private pendingCaptureBytes = 0;
  private pendingSpeech = false;
  private readyWaiters: Array<{
    resolve: () => void;
    reject: (e: Error) => void;
  }> = [];
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
    options: {
      mode?: "text" | "voice";
      conversationId?: string;
      taskId?: string;
      wakeTriggered?: boolean;
    } = {},
  ) {
    if (this.started || this.stopped) return;
    this.started = true;
    this.mode = options.mode ?? "voice";
    try {
      if (this.mode === "voice")
        await this.prepareCapture(options.wakeTriggered === true);
      if (this.stopped) return;
      // Permission may take as long as the user needs. Bound network/setup work
      // only after it is granted; cancellation is checked after every await.
      this.clearConnectTimer();
      this.connectTimer = setTimeout(
        () => this.fail("VOICE_CONNECT_TIMEOUT"),
        10000,
      );
      const ticket = await getTicket();
      if (this.stopped) {
        this.close();
        return;
      }
      const socket = new WebSocket(endpoint);
      this.socket = socket;
      socket.onopen = () => {
        if (!this.stopped && this.socket === socket)
          socket.send(
            JSON.stringify({
              ticket,
              language,
              mode: this.mode,
              conversation_id: options.conversationId,
              task_id: options.taskId,
              prebuffer_ms: 5000,
              ...(options.wakeTriggered === true && this.mode === "voice"
                ? { wake_triggered: true }
                : {}),
            }),
          );
      };
      this.bindCapture();
      socket.onmessage = (raw) => {
        if (this.stopped || this.socket !== socket) return;
        try {
          const event = JSON.parse(raw.data) as VoiceEvent;
          if (
            !event ||
            typeof event !== "object" ||
            typeof event.type !== "string"
          )
            throw new Error("VOICE_INVALID_MESSAGE");
          this.receive(event);
        } catch (error) {
          const code = error instanceof Error ? error.message : "";
          this.fail(
            [
              "AUDIO_CONNECTION_SLOW",
              "VOICE_INVALID_AUDIO",
              "VOICE_OUTPUT_MODE_MISMATCH",
            ].includes(code)
              ? code
              : "VOICE_INVALID_MESSAGE",
          );
        }
      };
      socket.onerror = () => this.fail("VOICE_CONNECTION_FAILED");
      socket.onclose = () => {
        if (this.stopped) return;
        this.close();
        this.onEvent({ type: "closed" });
      };
    } catch (error) {
      if (this.stopped) return;
      this.close();
      throw error;
    }
  }
  private async prepareCapture(afterWake = false) {
    const generation = ++this.captureGeneration;
    const context = this.context ?? new AudioContext();
    this.context = context;
    if (!afterWake) await context.resume();
    if (this.stopped || generation !== this.captureGeneration) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: microphoneConstraints(),
      video: false,
    });
    if (this.stopped || generation !== this.captureGeneration) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    this.stream = stream;
    this.clearConnectTimer();
    this.connectTimer = setTimeout(
      () => this.fail("VOICE_CONNECT_TIMEOUT"),
      10000,
    );
    // A wake event is not a click. Restore the previously authorized capture
    // before resuming Web Audio, so autoplay policy does not strand the handover.
    if (afterWake) await context.resume();
    if (this.stopped || generation !== this.captureGeneration) return;
    await context.audioWorklet.addModule("/audio-capture.js");
    if (this.stopped || generation !== this.captureGeneration) return;
    const capture = new AudioWorkletNode(context, "desk-capture");
    this.capture = capture;
    const input = context.createMediaStreamSource(stream);
    const mute = context.createGain();
    this.inputNode = input;
    this.muteNode = mute;
    mute.gain.value = 0;
    input.connect(capture).connect(mute).connect(context.destination);
    this.bindCapture();
  }
  private bindCapture() {
    const capture = this.capture,
      context = this.context;
    if (!capture || !context) return;
    capture.port.onmessage = (
      event: MessageEvent<
        ArrayBuffer | { pcm: ArrayBuffer; end_context_time: number }
      >,
    ) => {
      if (this.stopped || this.mode !== "voice") return;
      const pcm =
        event.data instanceof ArrayBuffer ? event.data : event.data.pcm;
      const endAt =
        performance.now() +
        (event.data instanceof ArrayBuffer
          ? 0
          : (event.data.end_context_time - context.currentTime) * 1000);
      if (!this.ready || this.socket?.readyState !== WebSocket.OPEN) {
        this.pendingSpeech ||= hasCaptureSpeech(pcm);
        this.pendingCapture.push({ pcm, endAt });
        this.pendingCaptureBytes += pcm.byteLength;
        // Keep a short silent preroll while the provider warms up. Silence
        // alone must not exhaust the five-second speech buffer before the
        // separate ten-second connection deadline has elapsed.
        if (!this.pendingSpeech) {
          while (
            this.pendingCaptureBytes > 16000 &&
            this.pendingCapture.length > 1
          )
            this.pendingCaptureBytes -=
              this.pendingCapture.shift()!.pcm.byteLength;
        }
        if (this.pendingCaptureBytes > 160000) {
          this.fail("VOICE_CONNECT_TIMEOUT");
          return;
        }
        return;
      }
      this.sendCapture(pcm, endAt);
    };
  }
  private sendCapture(pcm: ArrayBuffer, endAt: number, buffered = false) {
    const socket = this.socket;
    if (this.stopped || !this.ready || socket?.readyState !== WebSocket.OPEN)
      return;
    if (socket.bufferedAmount > (buffered ? 320000 : 64000)) {
      this.fail("AUDIO_CONNECTION_SLOW");
      return;
    }
    const wasVoiced = this.captureTimeline.voiced;
    const boundary = this.captureTimeline.observe(pcm, endAt);
    if (this.inputMarkers && !wasVoiced && this.captureTimeline.voiced)
      socket.send(JSON.stringify({ type: "input_started" }));
    if (!this.turn && this.captureTimeline.voiced && this.turnTimer !== null) {
      clearTimeout(this.turnTimer);
      this.turnTimer = null;
    }
    if (!this.turn && boundary) {
      const end = this.captureTimeline.endpoint(undefined, endAt);
      if (this.turnTimer !== null) clearTimeout(this.turnTimer);
      this.turnTimer = setTimeout(
        () => this.fail("VOICE_TURN_TIMEOUT"),
        Math.max(0, 10000 - (performance.now() - end.at)),
      );
    }
    let binary = "";
    for (const value of new Uint8Array(pcm))
      binary += String.fromCharCode(value);
    socket.send(JSON.stringify({ type: "audio", audio: btoa(binary) }));
    this.audioSent = true;
    if (boundary)
      socket.send(
        JSON.stringify({
          type: "input_ended",
          input_end_ms: this.captureTimeline.lastVoiceStreamMs,
        }),
      );
  }
  private receive(event: VoiceEvent) {
    if (event.type === "ready") {
      this.continuous = event.continuous === true;
      this.inputMarkers = event.input_markers === true;
      if (event.mode) this.mode = event.mode;
      this.ready = true;
      this.clearConnectTimer();
      const pending = this.pendingCapture;
      this.pendingCapture = [];
      this.pendingCaptureBytes = 0;
      this.pendingSpeech = false;
      for (const frame of pending)
        this.sendCapture(frame.pcm, frame.endAt, true);
      if (this.stopped) return;
      this.readyWaiters.splice(0).forEach((waiter) => waiter.resolve());
    }
    if (event.type === "interrupted") {
      this.clearPlayback();
      this.clearTurn();
    }
    if (event.type === "turn_waiting" && Number.isSafeInteger(event.turn_id)) {
      if (this.turn?.id !== event.turn_id) {
        if (!this.continuous) this.clearPlayback();
        this.clearTurn();
        const end =
          event.input_kind === "text"
            ? { at: performance.now(), source: "text_submit" }
            : this.captureTimeline.endpoint(
                event.input_end_ms,
                performance.now(),
              );
        this.turn = {
          id: event.turn_id!,
          end: end.at,
          endpoint: end.source,
          first: false,
          postTool: false,
          qualified: false,
        };
        // A suspended output context cannot turn an enqueued packet into a reply.
        this.turnTimer = setTimeout(
          () => this.fail("VOICE_TURN_TIMEOUT"),
          Math.max(0, 10000 - (performance.now() - end.at)),
        );
      }
    }
    if (event.type === "audio") {
      if (this.mode === "text") throw new Error("VOICE_OUTPUT_MODE_MISMATCH");
      if (typeof event.audio !== "string")
        throw new Error("VOICE_INVALID_AUDIO");
      if (event.turn_id !== undefined && event.turn_id !== this.turn?.id)
        return;
      this.play(event.audio, event.sample_rate ?? 24000, event);
    }
    // Provider completion can arrive seconds before the queued audio ends.
    if (event.type === "turn_complete") {
      if (event.turn_id !== undefined && event.turn_id !== this.turn?.id)
        return;
      if (event.mode === "text" || this.mode === "text") {
        this.clearTurn();
        this.onEvent(event);
        return;
      }
      this.completedTurnId = event.turn_id;
      this.completedTurn = true;
      this.finishPlayback();
      return;
    }
    if (
      event.type === "state" &&
      event.state === "listening" &&
      this.sources.size
    )
      return;
    if (
      event.type === "turn_timing" &&
      this.turn &&
      event.turn_id === this.turn.id
    ) {
      // Backend decides whether a post-tool frame is required for this turn.
      if (event.response_started) {
        this.turn.qualified = true;
        // Pre-tool filler audio does not clear either deadline.
        if (this.turnTimer !== null) clearTimeout(this.turnTimer);
        this.turnTimer = null;
        if (!this.sources.size && this.completedTurnId === this.turn.id)
          this.clearTurn();
      }
    }
    this.onEvent(event);
    if (event.type === "error" || event.type === "ended") this.close();
  }
  private waitReady() {
    if (this.stopped)
      return Promise.reject(new Error("VOICE_CONNECTION_FAILED"));
    if (this.ready) return Promise.resolve();
    return new Promise<void>((resolve, reject) =>
      this.readyWaiters.push({ resolve, reject }),
    );
  }
  async sendText(text: string) {
    await this.waitReady();
    if (
      !text.trim() ||
      text.length > 3000 ||
      this.socket?.readyState !== WebSocket.OPEN
    )
      throw new Error("INVALID_TEXT");
    this.socket.send(JSON.stringify({ type: "text", text }));
    this.audioSent = true; // An explicit input also admits opt-in image sharing.
  }
  refreshContext() {
    if (this.ready && this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(JSON.stringify({ type: "context_refresh" }));
  }
  async setMode(mode: "text" | "voice") {
    await this.waitReady();
    if (this.mode === mode) return;
    this.ready = false;
    this.clearPlayback();
    this.clearTurn();
    this.mode = mode;
    if (mode === "text") this.stopCapture();
    else {
      try {
        await this.prepareCapture();
      } catch (error) {
        this.stopCapture();
        this.mode = "text";
        this.ready = true;
        throw error;
      }
    }
    if (this.stopped) return;
    this.clearConnectTimer();
    this.connectTimer = setTimeout(
      () => this.fail("VOICE_CONNECT_TIMEOUT"),
      10000,
    );
    this.socket?.send(JSON.stringify({ type: "mode", mode }));
    await this.waitReady();
  }
  private stopCapture() {
    this.captureGeneration++;
    this.pendingCapture = [];
    this.pendingCaptureBytes = 0;
    this.pendingSpeech = false;
    this.inputNode?.disconnect();
    this.muteNode?.disconnect();
    this.inputNode = null;
    this.muteNode = null;
    if (this.capture) {
      this.capture.port.onmessage = null;
      this.capture.port.close();
      this.capture.disconnect();
      this.capture = null;
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
  private clearConnectTimer() {
    if (this.connectTimer !== null) clearTimeout(this.connectTimer);
    this.connectTimer = null;
  }
  private fail(code: string) {
    if (this.stopped) return;
    this.close();
    this.onEvent({ type: "error", code });
  }
  private finishPlayback() {
    if (this.stopped || !this.completedTurn || this.sources.size) return;
    this.completedTurn = false;
    if (this.socket?.readyState === WebSocket.OPEN)
      this.socket.send(
        JSON.stringify({
          type: "playback_ended",
          turn_id: this.completedTurnId,
        }),
      );
    this.onEvent({ type: "turn_complete", turn_id: this.completedTurnId });
    if (this.turn?.qualified) this.clearTurn();
  }
  private play(encoded: string, rate: number, event: VoiceEvent) {
    const context = this.context;
    if (!context) return;
    if (encoded.length > 640000) throw new Error("VOICE_INVALID_AUDIO");
    const raw = atob(encoded),
      bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    const pcm = new DataView(bytes.buffer),
      length = bytes.length / 2;
    if (rate !== 24000 || !length || bytes.length % 2 || length > 240000)
      throw new Error("VOICE_INVALID_AUDIO");
    const buffer = context.createBuffer(1, length, rate),
      values = buffer.getChannelData(0);
    let firstSound = -1;
    for (let i = 0; i < length; i++) {
      values[i] = pcm.getInt16(i * 2, true) / 32768;
      if (firstSound < 0 && Math.abs(values[i]) >= 0.001) firstSound = i;
    }
    this.nextTime = Math.max(context.currentTime + 0.02, this.nextTime);
    // Realtime providers can generate an ordinary calendar answer much faster
    // than it plays. Bound queued PCM to 30 seconds (about 2.9 MB float32),
    // including the incoming chunk, without cutting off an eight-second reply.
    if (this.nextTime + buffer.duration - context.currentTime > 30) {
      throw new Error("AUDIO_CONNECTION_SLOW");
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
      this.finishPlayback();
    };
    source.start(this.nextTime);
    if (
      firstSound >= 0 &&
      event.turn_id !== undefined &&
      event.audio_id !== undefined
    ) {
      this.marks.push({
        turn: event.turn_id,
        audio: event.audio_id,
        at: this.nextTime + firstSound / rate,
        afterTool: !!event.after_tool,
      });
      this.markTimer ??= setInterval(() => this.measurePlayback(), 20);
    }
    this.nextTime += buffer.duration;
  }
  private measurePlayback() {
    const context = this.context,
      turn = this.turn;
    if (!context || !turn) return;
    const pending: PendingPlaybackMark[] = [];
    for (const mark of this.marks) {
      if (mark.turn !== turn.id) continue;
      const stamp = renderedAt(context, mark.at, performance.now());
      if (!stamp) {
        pending.push(mark);
        continue;
      }
      const elapsed = stamp.at - turn.end;
      if (elapsed < 0) continue; // Clock disagreement is not a zero-ms response.
      if (turn.first && (!mark.afterTool || turn.postTool)) continue;
      turn.first = true;
      if (mark.afterTool) turn.postTool = true;
      if (this.socket?.readyState === WebSocket.OPEN)
        this.socket.send(
          JSON.stringify({
            type: "playback_started",
            turn_id: turn.id,
            audio_id: mark.audio,
            elapsed_ms: elapsed,
            timing_source: stamp.source,
            endpoint_source: turn.endpoint,
          }),
        );
    }
    if (
      !this.sources.size &&
      this.completedTurnId === turn.id &&
      this.socket?.readyState === WebSocket.OPEN
    )
      this.socket.send(
        JSON.stringify({ type: "playback_ended", turn_id: turn.id }),
      );
    this.marks = pending;
    if (!pending.length && this.markTimer !== null) {
      clearInterval(this.markTimer);
      this.markTimer = null;
    }
  }
  private clearTurn() {
    if (this.turnTimer !== null) clearTimeout(this.turnTimer);
    if (this.markTimer !== null) clearInterval(this.markTimer);
    this.turnTimer = null;
    this.markTimer = null;
    this.marks = [];
    this.turn = null;
  }
  interrupt() {
    this.clearPlayback();
    this.clearTurn();
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
  shareCameraFrame(video: HTMLVideoElement) {
    if (!this.visionReady() || video.readyState < 2)
      throw new Error("VOICE_VISION_NOT_READY");
    this.stopVision();
    try {
      this.sendImage(
        encodeVoiceImage(video, video.videoWidth, video.videoHeight),
      );
    } finally {
      this.stopVision();
    }
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
    this.completedTurn = false;
    this.completedTurnId = undefined;
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
    this.clearConnectTimer();
    this.clearTurn();
    this.readyWaiters
      .splice(0)
      .forEach((waiter) => waiter.reject(new Error("VOICE_CONNECTION_FAILED")));
    this.stopCapture();
    this.stopVision();
    this.clearPlayback();
    if (this.socket) {
      const socket = this.socket;
      this.socket = null;
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      socket.close();
    }
    this.meter?.close();
    this.meter = null;
    if (this.context) {
      void this.context.close().catch(() => {});
      this.context = null;
    }
  }
}
