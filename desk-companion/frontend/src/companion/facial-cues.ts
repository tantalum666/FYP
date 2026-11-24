import type { Delivery } from "./delivery.ts";
import type { CompanionState } from "./interaction.ts";
import type { AliceGesture } from "./motion-cues.ts";
import type { FaceCue } from "./performance-pose.ts";

function ease(x: number) {
  const t = Math.max(0, Math.min(1, x));
  return t * t * (3 - 2 * t);
}

/** Social delivery owns the expression through the reply. Listening and
 * thought have a quiet face even between movements of the body. */
export function conversationalFace(
  state: CompanionState,
  gesture: AliceGesture | null,
  age: number,
  weight: number,
  delivery: Delivery | undefined,
  scored: FaceCue | null,
): FaceCue | null {
  if (gesture && delivery === "relieved")
    return {
      face: "relieved",
      weight,
      wink: 0,
      eyelids: 0.57 * ease(age / 0.48) * ease((2.36 - age) / 0.88),
      mouthFace: age < 1.45 ? "relieved" : "appreciate",
    };
  if (gesture && delivery === "bashful")
    return {
      face: "bashful",
      weight,
      wink: 0,
      eyelids: 0.3 * ease(age / 0.64) * ease((2.05 - age) / 0.64),
    };
  if (gesture && delivery === "apologetic")
    return {
      face: "apologetic",
      weight,
      wink: 0,
      eyelids: 0.2 * ease(age / 0.28) * ease((1.38 - age) / 0.5),
    };
  if (scored) return scored;
  if (gesture === "wave")
    return { face: "appreciate", weight: weight * 0.6, wink: 0 };
  if (state === "thinking")
    return { face: "pensive", weight: 0.62 + 0.19 * weight, wink: 0 };
  if (state === "listening")
    return { face: "attentive", weight: 0.54 + 0.19 * weight, wink: 0 };
  return null;
}
