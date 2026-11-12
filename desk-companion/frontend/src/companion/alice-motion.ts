import { companionState, type CompanionState } from "./interaction.ts";

export const MOTION_BONES = [
  "spine",
  "chest",
  "neck",
  "head",
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
export const GREETING_SECONDS = 4.8;

function smooth(value: number) {
  const x = Math.max(0, Math.min(1, value));
  return x * x * x * (x * (x * 6 - 15) + 10);
}

/** A bounded gesture returns to rest, with zero velocity at both ends. */
export function gestureWeight(age: number, duration = GREETING_SECONDS) {
  if (!Number.isFinite(age) || age < 0 || age >= duration) return 0;
  const weight = smooth(age / 1.15) * smooth((duration - age) / 1.35);
  return weight < 1e-6 ? 0 : weight;
}

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
    gesture?: "wave" | "nod";
    gestureAt?: number;
    waveSide?: "left" | "right";
  } = {},
): {
  pose: MotionPose;
  smile: number;
  state: CompanionState;
  gesture: "wave" | "nod" | null;
  openness: number;
} {
  const t = Math.max(0, Number.isFinite(time) ? time : 0);
  const state = companionState(options.state ?? "idle");
  const pose = Object.fromEntries(
    MOTION_BONES.map((name) => [name, [0, 0, 0]]),
  ) as MotionPose;
  const breath = Math.sin(t * 1.35);
  const settle = Math.sin(t * 0.62);
  const glanceAge = t % 24;
  const glance =
    glanceAge > 8 && glanceAge < 12
      ? Math.sin(((glanceAge - 8) / 4) * Math.PI) * 0.13
      : glanceAge > 18 && glanceAge < 22
        ? -Math.sin(((glanceAge - 18) / 4) * Math.PI) * 0.1
        : 0;
  const finiteLook = (value = 0) =>
    Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0;
  pose.spine = [0.004 * breath, 0.009 * settle, 0.012 * settle];
  pose.chest = [0.012 * breath, 0.008 * Math.sin(t * 0.43), -0.006 * settle];
  pose.neck = [0.006 * breath, 0, 0.012 * Math.sin(t * 0.73)];
  pose.head = [
    finiteLook(options.lookY) * 0.045 + Math.sin(t * 0.57) * 0.025,
    finiteLook(options.lookX) * 0.12 + (state === "idle" ? glance : 0),
    0.017 * settle,
  ];
  pose.leftUpperArm = [0.018 * breath, 0, 0.018 * settle];
  pose.rightUpperArm = [-0.018 * breath, 0, 0.018 * settle];
  pose.leftLowerArm = [-0.025, 0, -0.07 - 0.025 * breath];
  pose.rightLowerArm = [-0.025, 0, 0.07 + 0.025 * breath];

  let smile = 0.025;
  if (state === "listening") {
    pose.chest[0] += 0.025;
    pose.head[0] += 0.035 + Math.max(0, Math.sin(t * 1.55)) * 0.035;
    pose.head[2] += 0.065;
    smile = 0.06;
  } else if (state === "thinking") {
    pose.head[0] -= 0.055;
    pose.head[1] += 0.075;
    pose.head[2] -= 0.045;
    pose.leftLowerArm[2] -= 0.1;
  } else if (state === "speaking") {
    // Deliberate small phrases, rather than shaking in sync with every audio sample.
    const phrase = Math.pow(0.5 + 0.5 * Math.sin(t * 1.7), 2);
    pose.head[0] += 0.025 * Math.sin(t * 3.4);
    pose.chest[1] += 0.025 * Math.sin(t * 1.15);
    pose.leftUpperArm[2] -= 0.09 * phrase;
    pose.leftLowerArm[2] -= 0.26 * phrase;
    pose.leftHand[1] += 0.12 * phrase;
    pose.rightLowerArm[2] += 0.16 * (1 - phrase);
    smile = 0.07;
  }

  const age = t - (options.gestureAt ?? -100);
  const weight = gestureWeight(
    age,
    options.gesture === "nod" ? 1.2 : GREETING_SECONDS,
  );
  const gesture = weight > 0 ? (options.gesture ?? null) : null;
  if (gesture === "wave") {
    const side = options.waveSide ?? "left";
    const sign = side === "left" ? -1 : 1;
    const blend = (bone: MotionBone, target: Rotation, amount = weight) => {
      pose[bone] = target.map(
        (value, axis) => pose[bone][axis] * (1 - amount) + value * amount,
      ) as Rotation;
    };
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
    pose.head[0] +=
      Math.sin((Math.max(0, age) * Math.PI) / 1.2) * 0.12 * weight;
    smile = Math.max(smile, 0.13 * weight);
  }
  return {
    pose,
    smile,
    state,
    gesture,
    openness: gesture === "wave" ? weight : 0,
  };
}
