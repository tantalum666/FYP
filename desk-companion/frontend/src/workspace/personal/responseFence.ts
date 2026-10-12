/** A response may only enter the view in the exact privacy/session epoch that requested it. */
export class ResponseFence {
  private identity = "";
  private visible = false;
  version = 0;
  update(identity: string, visible: boolean) {
    if (identity !== this.identity || visible !== this.visible) this.version++;
    this.identity = identity;
    this.visible = visible;
  }
  capture() {
    return this.version;
  }
  accepts(token: number) {
    return this.visible && token === this.version;
  }
}
