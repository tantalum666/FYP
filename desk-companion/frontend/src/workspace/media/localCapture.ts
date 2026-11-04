/** One owner for a browser device stream, including late permission results. */
export class LocalCapture {
  private generation = 0;
  private stream: MediaStream | null = null;
  private acquire: (
    constraints: MediaStreamConstraints,
  ) => Promise<MediaStream>;
  pending = false;
  constructor(
    acquire = (constraints: MediaStreamConstraints) =>
      navigator.mediaDevices.getUserMedia(constraints),
  ) {
    this.acquire = acquire;
  }

  async start(
    constraints: MediaStreamConstraints,
  ): Promise<MediaStream | null> {
    this.stop();
    const generation = this.generation;
    this.pending = true;
    try {
      const stream = await this.acquire(constraints);
      if (generation !== this.generation) {
        stream.getTracks().forEach((track) => track.stop());
        return null;
      }
      this.stream = stream;
      return stream;
    } catch (error) {
      if (generation !== this.generation) return null;
      throw error;
    } finally {
      if (generation === this.generation) this.pending = false;
    }
  }
  owns(stream: MediaStream) {
    return this.stream === stream;
  }
  stop() {
    this.generation++;
    this.pending = false;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
}
