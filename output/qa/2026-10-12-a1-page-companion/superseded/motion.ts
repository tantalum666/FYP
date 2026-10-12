export type Gesture = "none" | "nod" | "wave" | "step";

/** A bounded response envelope shared by the real 3D skeleton's joints. */
export function gesturePose(kind: Gesture, elapsed: number) {
  const progress = Math.max(0, Math.min(1, elapsed / 1.7));
  const envelope = Math.sin(Math.PI * progress) ** 2;
  return {
    nod: kind === "nod" ? envelope * 0.15 : 0,
    wrist:
      kind === "wave" ? envelope * Math.sin(progress * Math.PI * 6) * 0.07 : 0,
    step: kind === "step" ? envelope : 0,
    greet: kind === "wave" ? envelope : 0,
  };
}
