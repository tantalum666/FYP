export const deliveries = [
  "neutral",
  "celebrate",
  "comfort",
  "appreciate",
  "surprised",
  "amused",
  "curious",
  "encourage",
] as const;
export type Delivery = (typeof deliveries)[number];

// Live captions and older desks can supply text without a delivery field.
// Only recognize an explicit response from Alice; a quoted story is ambiguous.
const openings: readonly [Delivery, RegExp][] = [
  [
    "comfort",
    /^(?:听起来你|聽落你|听到这个我很难过|很遗憾|抱抱你|that sounds (?:really |so )?(?:hard|rough|painful)|i['’]m (?:really |so )?sorry (?:to hear|that you))/i,
  ],
  [
    "celebrate",
    /^(?:恭喜|太棒了|真替你高兴|真替你高興|好叻|congratulations\b|congrats\b|you did it\b)/i,
  ],
  [
    "appreciate",
    /^(?:不客气|不客氣|唔使客氣|不用谢|you['’]re (?:very |so )?welcome\b|my pleasure\b)/i,
  ],
  ["amused", /^(?:哈哈|笑死|哈哈哈|ha(?:ha)+\b|that made me laugh\b)/i],
  ["surprised", /^(?:没想到|冇諗到|wow[,! ]|what a surprise\b)/i],
  [
    "encourage",
    /^(?:加油|慢慢来|慢慢嚟|you['’]ve got this\b|one step at a time\b)/i,
  ],
];

export function replyDelivery(value: unknown, message: string): Delivery {
  if (deliveries.includes(value as Delivery)) return value as Delivery;
  const opening = message.trimStart().slice(0, 75);
  return (
    openings.find(([, pattern]) => pattern.test(opening))?.[0] ?? "neutral"
  );
}

/** One visible reaction per spoken answer, including captions split across packets. */
export class SpokenDelivery {
  private opening = "";
  private reacted = false;
  private group = -1;
  private finishedGroup = -1;
  finish() {
    this.finishedGroup = this.group;
    this.opening = "";
    this.reacted = false;
  }
  receive(event: {
    role?: string;
    text?: string;
    caption_group?: number;
    final?: boolean;
  }): Delivery | null {
    if (event.role !== "assistant" || !event.text || this.reacted) return null;
    if (Number.isSafeInteger(event.caption_group)) {
      const group = event.caption_group!;
      if (group <= this.finishedGroup || group < this.group) return null;
      this.group = group;
    }
    this.opening = (
      event.final && !Number.isSafeInteger(event.caption_group)
        ? event.text
        : this.opening + event.text
    ).slice(0, 75);
    const delivery = replyDelivery(undefined, this.opening);
    if (delivery === "neutral") return null;
    this.reacted = true;
    return delivery;
  }
}
