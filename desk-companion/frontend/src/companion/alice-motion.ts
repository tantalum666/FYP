import { companionState, type CompanionState } from "./interaction.ts";
import {
  GESTURE_SECONDS,
  gestureWeight,
  easeMotion as smooth,
  type AliceGesture,
} from "./motion-cues.ts";
export { gestureWeight } from "./motion-cues.ts";

export const MOTION_BONES = [
  "spine",
  "chest",
  "neck",
  "head",
  "leftShoulder",
  "rightShoulder",
  "leftUpperArm",
  "rightUpperArm",
  "leftLowerArm",
  "rightLowerArm",
  "leftHand",
  "rightHand",
] as const;
export type MotionBone = (typeof MOTION_BONES)[number];
type Rotation = [number, number, number];
export type MotionPose = Record<MotionBone, Rotation>;
export const GREETING_SECONDS = GESTURE_SECONDS.wave;

export function blinkWeight(time: number) {
  // Unequal intervals and an occasional double blink, without a random timer.
  const intervals = [4.6, 6.1, 3.8, 5.4];
  let age = Math.max(0, Number.isFinite(time) ? time : 0) % 19.9;
  for (const [index, duration] of intervals.entries()) {
    if (age < duration) {
      const close = Math.exp(-Math.pow((age - duration + 0.22) / 0.065, 2));
      const double =
        index === 2
          ? Math.exp(-Math.pow((age - duration + 0.52) / 0.06, 2)) * 0.8
          : 0;
      return Math.min(1, close + double);
    }
    age -= duration;
  }
  return 0;
}

/** Offsets from the model's own relaxed pose; root, hips, legs and feet stay planted. */
export function aliceMotion(
  time: number,
  options: {
    state?: string;
    lookX?: number;
    lookY?: number;
    gesture?: AliceGesture;
    gestureAt?: number;
    waveSide?: "left" | "right";
  } = {},
): {
  pose: MotionPose;
  smile: number;
  state: CompanionState;
  gesture: AliceGesture | null;
  openness: number;
} {
  const t = Math.max(0, Number.isFinite(time) ? time : 0);
  const state = companionState(options.state ?? "idle");
  const pose = Object.fromEntries(
    MOTION_BONES.map((name) => [name, [0, 0, 0]]),
  ) as MotionPose;
  const breath = Math.sin(t * 1.35);
  const settle = Math.sin(t * 0.62);
  const finiteLook = (value = 0) =>
    Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0;
  pose.spine = [0.004 * breath, 0.006 * settle, 0.008 * settle];
  pose.chest = [0.012 * breath, 0.006 * Math.sin(t * 0.43), -0.004 * settle];
  pose.neck = [0.006 * breath, 0, 0.008 * Math.sin(t * 0.73)];
  pose.head = [
    finiteLook(options.lookY) * 0.045 + Math.sin(t * 0.57) * 0.025,
    finiteLook(options.lookX) * 0.12,
    0.017 * settle,
  ];
  pose.leftUpperArm = [0.018 * breath, 0, 0.018 * settle];
  pose.rightUpperArm = [-0.018 * breath, 0, 0.018 * settle];
  pose.leftLowerArm = [-0.025, 0, -0.07 - 0.025 * breath];
  pose.rightLowerArm = [-0.025, 0, 0.07 + 0.025 * breath];

  let smile = 0.025;
  if (state === "listening") {
    pose.chest[0] += 0.025;
    pose.head[0] += 0.025;
    smile = 0.06;
  } else if (state === "thinking") {
    pose.head[0] -= 0.025;
    pose.head[1] += 0.025;
  } else if (state === "speaking") {
    // Longer phrase gestures are sequenced separately, with actual quiet gaps.
    pose.chest[0] += 0.015;
    smile = 0.07;
  }

  const age = t - (options.gestureAt ?? -100);
  const weight = gestureWeight(
    age,
    options.gesture ? GESTURE_SECONDS[options.gesture] : GREETING_SECONDS,
  );
  const gesture = weight > 0 ? (options.gesture ?? null) : null;
  const blend = (bone: MotionBone, target: Rotation, amount = weight) => {
    pose[bone] = target.map(
      (value, axis) => pose[bone][axis] * (1 - amount) + value * amount,
    ) as Rotation;
  };
  if (gesture === "wave") {
    const side = options.waveSide ?? "left";
    const sign = side === "left" ? -1 : 1;
    const elbow = smooth(age / 0.95) * smooth((GREETING_SECONDS - age) / 1.1);
    const wrist =
      smooth((age - 0.25) / 1.1) * smooth((GREETING_SECONDS - age - 0.1) / 1.0);
    const wave = smooth((age - 1.2) / 0.45) * smooth((3.45 - age) / 0.55);
    const phase = (age - 1.2) * Math.PI * 2 * 0.85;
    blend(`${side}UpperArm`, [
      -0.12,
      0,
      sign * (0.56 + 0.018 * Math.sin(phase - 0.7) * wave),
    ]);
    blend(
      `${side}LowerArm`,
      [-0.08, 0, sign * (2.24 + 0.035 * Math.sin(phase - 0.35) * wave)],
      elbow,
    );
    // Bring the forearm forward during the lift, then show the palm beside
    // the face. A flat sideways sweep would clip the phone's right edge.
    pose[`${side}UpperArm`][0] -= Math.sin(Math.PI * weight) * 1.0;
    blend(
      `${side}Hand`,
      [
        // Both normalized wrists use the same forward roll. Mirroring this
        // sign turns the right palm away on Alice's actual VRM0 skeleton.
        1.35,
        Math.sin(phase - 0.25) * 0.035 * wave,
        sign * (0.025 + Math.sin(phase) * 0.09 * wave),
      ],
      wrist,
    );
    pose.chest[1] += -sign * 0.018 * weight;
    pose.head[2] += -sign * 0.035 * weight;
    smile = Math.max(smile, 0.17 * weight);
  } else if (gesture === "nod") {
    const dip = smooth(age / 0.65) * (1 - smooth((age - 0.9) / 0.85));
    pose.head[0] += 0.18 * dip;
    pose.chest[0] += 0.025 * weight;
    pose.head[2] += 0.035 * weight;
    smile = Math.max(smile, 0.21 * weight);
  } else if (gesture === "curious") {
    pose.head[2] += 0.15 * weight;
    pose.head[1] -= 0.055 * weight;
    pose.neck[2] += 0.025 * weight;
    pose.chest[2] -= 0.035 * weight;
    pose.rightShoulder[2] += 0.035 * weight;
    smile = Math.max(smile, 0.14 * weight);
  } else if (gesture === "glance") {
    const direction = Math.floor((options.gestureAt ?? 0) / 7) % 2 ? -1 : 1;
    pose.head[1] += direction * 0.23 * weight;
    pose.chest[1] += direction * 0.065 * weight;
    pose.head[0] -= 0.025 * weight;
  } else if (gesture === "relax") {
    pose.leftShoulder[2] -= 0.055 * weight;
    pose.rightShoulder[2] += 0.055 * weight;
    pose.chest[0] -= 0.04 * weight;
    pose.head[0] -= 0.045 * weight;
    pose.leftLowerArm[2] -= 0.18 * weight;
    pose.rightLowerArm[2] += 0.16 * weight;
    pose.leftHand[0] += 0.12 * weight;
    pose.rightHand[0] += 0.12 * weight;
  } else if (gesture === "ponder") {
    pose.head[0] -= 0.065 * weight;
    pose.head[1] += 0.13 * weight;
    pose.head[2] -= 0.085 * weight;
    pose.chest[1] += 0.04 * weight;
    pose.leftLowerArm[2] -= 0.24 * weight;
    pose.leftShoulder[0] -= 0.025 * weight;
  } else if (gesture === "explain") {
    const side = options.waveSide ?? "left";
    const sign = side === "left" ? -1 : 1;
    const hand =
      smooth((age - 0.3) / 1.1) *
      smooth((GESTURE_SECONDS.explain - age) / 1.25);
    pose[`${side}Shoulder`][0] -= 0.04 * weight;
    // Keep the forearm forward and inside the narrow phone silhouette.
    blend(`${side}UpperArm`, [-0.4, 0, sign * 0.05]);
    blend(`${side}LowerArm`, [-0.5, 0, sign * 1.8]);
    blend(`${side}Hand`, [1.35, 0, 0], hand);
    pose.chest[1] -= sign * 0.045 * weight;
    pose.head[2] += sign * 0.04 * weight;
    pose.head[0] += 0.035 * weight;
    smile = Math.max(smile, 0.13 * weight);
  }
  return {
    pose,
    smile,
    state,
    gesture,
    openness: gesture === "wave" || gesture === "explain" ? weight : 0,
  };
}
