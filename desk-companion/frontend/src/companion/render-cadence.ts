/** Schedule at 30 Hz on the display's rAF clock. Keep its fractional phase. */
export class RenderCadence {
  private previous: number | null = null;
  private next = 0;

  reset() {
    this.previous = null;
  }

  sample(at: number): number | null {
    const period = 1000 / 30;
    if (this.previous === null) {
      this.previous = at;
      this.next = at + period;
      return 0;
    }
    // rAF can arrive just before a deadline on a 60 or 120 Hz display.
    const due = at + 2 - this.next;
    if (due < 0) return null;
    this.next += (1 + Math.floor(due / period)) * period;
    const elapsed = Math.min((at - this.previous) / 1000, 0.25);
    this.previous = at;
    return elapsed;
  }
}
