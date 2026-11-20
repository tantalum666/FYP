import { companionState, type CompanionState } from "./interaction.ts";
import {
  deliveryPerformances,
  performanceDurations,
  type Face,
} from "./performance-score.ts";
import type { Delivery } from "./delivery.ts";

export const GESTURE_SECONDS = {
  ...performanceDurations,
  wave: 4.8,
  nod: 2.4,
  curious: 4.2,
  explain: 5.2,
  glance: 4.6,
  relax: 5.4,
  ponder: 5.0,
} as const;
export type AliceGesture = keyof typeof GESTURE_SECONDS;
export type MotionCue = { gesture: AliceGesture; gestureAt: number };

export function easeMotion(value: number) {
  const x = Math.max(0, Math.min(1, value));
  return x * x * x * (x * (x * 6 - 15) + 10);
}

/** Shared by pose sampling and input coalescing, including the quiet tail. */
export function gestureWeight(
  age: number,
  duration: number = GESTURE_SECONDS.wave,
) {
  if (!Number.isFinite(age) || age < 0 || age >= duration) return 0;
  const weight = easeMotion(age / 1.15) * easeMotion((duration - age) / 1.35);
  return weight < 1e-6 ? 0 : weight;
}

const sequences: Record<CompanionState, readonly AliceGesture[]> = {
  idle: ["glance", "hairTuck", "relax", "sleeveAdjust", "curious"],
  listening: ["curious", "nod", "curious"],
  thinking: ["ponder", "chinRest", "glance"],
  speaking: ["explain", "nod", "explain"],
};
const pauses: Record<CompanionState, readonly number[]> = {
  idle: [11, 17, 13, 20],
  listening: [5, 9, 7],
  thinking: [7, 11],
  speaking: [1.8, 3.4, 2.6],
};
const hellos: readonly AliceGesture[] = [
  "wave",
  "wink",
  "gratefulBow",
  "nod",
  "curious",
  "explain",
];

/** Short, contextual gestures with quiet gaps. Uses the renderer's clock only. */
export class MotionCues {
  private state: CompanionState = "idle";
  private cue: MotionCue | null = null;
  private nextAt = 11;
  private index = 0;
  private helloIndex = 0;
  private helloCue: MotionCue | null = null;
  private delivery: Delivery = "neutral";
  get activeDelivery() {
    return this.delivery;
  }
  private variants = new Map<Face, number>();

  dismissReply() {
    if (this.delivery !== "neutral") this.cue = null;
    this.delivery = "neutral";
  }

  respond(time: number, delivery: Delivery) {
    this.dismissReply();
    if (delivery === "neutral") return;
    const choices = deliveryPerformances[delivery],
      index = this.variants.get(delivery) ?? 0;
    const gesture = choices[index % choices.length];
    this.variants.set(delivery, index + 1);
    this.cue = { gesture, gestureAt: time };
    this.delivery = delivery;
    this.helloCue = null;
    this.nextAt = time + GESTURE_SECONDS[gesture] + pauses[this.state][0];
  }

  greeting(time: number) {
    if (this.state !== "idle") return;
    this.helloIndex = 1;
    this.cue = { gesture: "wave", gestureAt: time + 0.35 };
    this.helloCue = this.cue;
    this.nextAt = time + 18;
  }

  hello(time: number) {
    if (this.delivery !== "neutral") return;
    // Rapid taps acknowledge the current gesture, rather than restarting its arm.
    if (
      this.helloCue &&
      (time < this.helloCue.gestureAt ||
        gestureWeight(
          time - this.helloCue.gestureAt,
          GESTURE_SECONDS[this.helloCue.gesture],
        ) > 0)
    )
      return;
    const gesture =
      this.state === "idle" ? hellos[this.helloIndex++ % hellos.length] : "nod";
    this.cue = { gesture, gestureAt: time };
    this.helloCue = this.cue;
    this.nextAt = time + GESTURE_SECONDS[gesture] + pauses[this.state][0];
  }

  sample(time: number, input: string): MotionCue | null {
    if (!Number.isFinite(time) || time < 0) return null;
    const state = companionState(input);
    if (state !== this.state) {
      this.state = state;
      this.index = 0;
      if (this.delivery === "neutral") {
        this.cue = null;
        this.helloCue = null;
        // A newly heard person gets attention; returning to idle gets a quiet pause.
        this.nextAt = time + (state === "idle" ? 8 : 0.35);
      }
    }
    if (
      this.cue &&
      time >= this.cue.gestureAt + GESTURE_SECONDS[this.cue.gesture]
    ) {
      this.cue = null;
      this.delivery = "neutral";
    }
    if (!this.cue && time >= this.nextAt) {
      const gesture = sequences[state][this.index % sequences[state].length];
      const pause = pauses[state][this.index % pauses[state].length];
      this.index++;
      this.cue = { gesture, gestureAt: time };
      this.nextAt = time + GESTURE_SECONDS[gesture] + pause;
    }
    return this.cue;
  }
}
