export interface PrivateOperation {
  path: string;
  serialized: string;
  key: string;
}
export class PrivateWriteError extends Error {
  code: string;
  constructor(code: string) {
    super(code);
    this.code = code;
  }
}
type Transport = (operation: Readonly<PrivateOperation>) => Promise<unknown>;

/** Component-lifetime recovery only. Never writes text or IDs to browser storage. */
export class PrivateWriteQueue {
  private operation: PrivateOperation | null = null;
  private running = false;
  private transport: Transport;
  private newId: () => string;
  constructor(transport: Transport, newId: () => string) {
    this.transport = transport;
    this.newId = newId;
  }
  get pending() {
    return this.operation !== null;
  }
  get active() {
    return this.running;
  }
  async send<T>(path: string, body: unknown): Promise<T> {
    if (this.running) throw new PrivateWriteError("PRIVATE_WRITE_BUSY");
    const serialized = JSON.stringify(body);
    if (
      this.operation &&
      (this.operation.path !== path || this.operation.serialized !== serialized)
    )
      throw new PrivateWriteError("PRIVATE_WRITE_PENDING");
    this.operation ??= { path, serialized, key: this.newId() };
    return this.dispatch<T>();
  }
  async retry<T>(): Promise<T> {
    if (!this.operation) throw new PrivateWriteError("PRIVATE_WRITE_MISSING");
    if (this.running) throw new PrivateWriteError("PRIVATE_WRITE_BUSY");
    return this.dispatch<T>();
  }
  private async dispatch<T>(): Promise<T> {
    const operation = this.operation!;
    this.running = true;
    try {
      const result = await this.transport(operation);
      if (this.operation === operation) this.operation = null;
      return result as T;
    } catch (error) {
      const status =
        typeof error === "object" && error !== null && "status" in error
          ? Number(error.status)
          : 0;
      // A network timeout is not evidence of failure. Keep exactly the same ID.
      if (status >= 400 && status < 500 && status !== 401 && status !== 408)
        if (this.operation === operation) this.operation = null;
      throw error;
    } finally {
      this.running = false;
    }
  }
  clear() {
    this.operation = null;
  }
}
