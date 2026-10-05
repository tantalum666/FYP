// Mono, little-endian PCM16 at 16 kHz, in 40 ms chunks. No recording storage.
class DeskCapture extends AudioWorkletProcessor {
  constructor() { super(); this.buffer = []; this.position = 0; this.chunk = []; }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) return true;
    this.buffer.push(...input);
    const ratio = sampleRate / 16000;
    while (this.position + 1 < this.buffer.length) {
      const i = Math.floor(this.position), fraction = this.position - i;
      const value = this.buffer[i] * (1-fraction) + this.buffer[i+1]*fraction;
      this.chunk.push(Math.round(Math.max(-1, Math.min(1, value))*32767));
      this.position += ratio;
      if (this.chunk.length === 640) {
        const pcm = new ArrayBuffer(1280), view = new DataView(pcm);
        this.chunk.forEach((v, index) => view.setInt16(index*2, v, true));
        this.port.postMessage(pcm, [pcm]); this.chunk = [];
      }
    }
    const consumed = Math.min(Math.floor(this.position), this.buffer.length);
    this.buffer.splice(0, consumed); this.position -= consumed;
    return true;
  }
}
registerProcessor('desk-capture', DeskCapture);
