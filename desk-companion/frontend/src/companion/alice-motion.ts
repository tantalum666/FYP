import { transferWristRoll } from "./arm-anatomy.ts";
import { companionState, type CompanionState } from "./interaction.ts";
import {
  GESTURE_SECONDS,
  gestureWeight,
  easeMotion as smooth,
  type AliceGesture,
} from "./motion-cues.ts";
export { gestureWeight } from "./motion-cues.ts";
import {
  applyPerformance,
  isPerformance,
  type FaceCue,
  type HandShapes,
} from "./performance-pose.ts";

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

/** One movement from rest through an accent and back, in seconds. */
function stroke(age: number, start: number, peak: number, end: number) {
  return age < peak
    ? smooth((age - start) / (peak - start))
    : smooth((end - age) / (end - peak));
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
  gaze: { yaw: number; pitch: number };
  face: FaceCue | null;
  hands: HandShapes | null;
} {
  const t = Math.max(0, Number.isFinite(time) ? time : 0);
  const state = companionState(options.state ?? "idle");
  const pose = Object.fromEntries(
    MOTION_BONES.map((name) => [name, [0, 0, 0]]),
  ) as MotionPose;
  const breath = Math.sin(t * 1.35 + 0.18 * Math.sin(t * 0.31));
  const settle = Math.sin(t * 0.62);
  const finiteLook = (value = 0) =>
    Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0;
  const lookX = finiteLook(options.lookX),
    lookY = finiteLook(options.lookY);
  const gaze = { yaw: lookX * 20, pitch: -lookY * 12 };
  pose.spine = [0.005 * breath, 0.009 * settle, 0.018 * settle];
  pose.chest = [0.014 * breath, 0.008 * Math.sin(t * 0.43), -0.009 * settle];
  pose.neck = [0.006 * breath, 0, 0.008 * Math.sin(t * 0.73)];
  pose.head = [
    lookY * 0.045 + Math.sin(t * 0.57) * 0.025,
    lookX * 0.12,
    0.017 * settle,
  ];
  pose.leftShoulder[2] = -0.016 * breath;
  pose.rightShoulder[2] = 0.012 * breath;
  // The wrists rest a little in front of the skirt, at different depths.
  // Counter-rotate the upper arms so the elbows stay close to the silhouette.
  pose.leftUpperArm = [-0.1 + 0.018 * breath, 0, 0.055 + 0.018 * settle];
  pose.rightUpperArm = [-0.065 - 0.015 * breath, 0, -0.035 + 0.014 * settle];
  pose.leftLowerArm = [-0.035, -0.32, 0.04 - 0.025 * breath];
  pose.rightLowerArm = [-0.025, 0.21, -0.04 + 0.02 * breath];
  pose.leftHand[0] = 0.09;
  pose.rightHand[0] = 0.06;

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
  const side = options.waveSide ?? "left";
  const sign = side === "left" ? -1 : 1;
  let openness = 0;
  const blend = (bone: MotionBone, target: Rotation, amount = weight) => {
    pose[bone] = target.map(
      (value, axis) => pose[bone][axis] * (1 - amount) + value * amount,
    ) as Rotation;
  };
  if (gesture === "wave") {
    const elbow = smooth(age / 0.95) * smooth((GREETING_SECONDS - age) / 1.1);
    const wrist =
      smooth((age - 0.25) / 1.1) * smooth((GREETING_SECONDS - age - 0.1) / 1.0);
    // Two unequal sweeps. The elbow sets the direction and the wrist trails.
    const sweep = (a: number) =>
      stroke(a, 1.05, 1.68, 2.24) -
      0.85 * stroke(a, 1.7, 2.26, 2.84) +
      0.63 * stroke(a, 2.29, 2.89, 3.53);
    const lead = sweep(age),
      follow = sweep(age - 0.12);
    const lift = stroke(age, 0, 1.05, 3.95);
    const settleBack = stroke(age, 2.95, 4.03, GREETING_SECONDS);
    pose[`${side}Shoulder`][0] -= 0.075 * lift;
    pose.spine[2] += sign * (0.032 * lift - 0.019 * settleBack);
    blend(`${side}UpperArm`, [-0.12, 0, sign * (0.56 + 0.042 * lead)]);
    blend(
      `${side}LowerArm`,
      [-0.08 - 0.065 * lead, 0, sign * (2.24 + 0.072 * lead)],
      elbow,
    );
    blend(
      `${side}Hand`,
      [
        // Both normalized wrists use the same forward roll. Mirroring this
        // sign turns the right palm away on Alice's actual VRM0 skeleton.
        1.35,
        0.055 * follow,
        sign * (0.025 + 0.17 * follow),
      ],
      wrist,
    );
    openness = wrist;
    pose.chest[1] -= sign * (0.05 * lift + 0.017 * lead);
    pose.head[2] -= sign * 0.06 * stroke(age, 0.15, 1.46, 4.28);
    smile = Math.max(smile, 0.17 * weight);
  } else if (gesture === "nod") {
    const dip = stroke(age, 0.13, 0.72, 1.62);
    pose.head[0] += 0.19 * dip - 0.035 * stroke(age, 1.16, 1.65, 2.32);
    pose.chest[0] += 0.036 * stroke(age, 0.32, 0.99, 2.18);
    pose.head[2] += 0.035 * weight;
    smile = Math.max(smile, 0.21 * weight);
  } else if (gesture === "curious") {
    const tilt = stroke(age, 0.16, 1.23, 4.15);
    const lean = stroke(age, 0.48, 1.94, 4.2);
    gaze.yaw -= 9 * stroke(age, 0, 0.26, 1.48);
    pose.head[2] += 0.18 * tilt;
    pose.head[1] -= 0.075 * tilt;
    pose.neck[2] += 0.036 * lean;
    pose.chest[2] -= 0.062 * lean;
    pose.rightShoulder[2] += 0.055 * lean;
    smile = Math.max(smile, 0.14 * weight);
  } else if (gesture === "glance") {
    const direction = Math.floor((options.gestureAt ?? 0) / 7) % 2 ? -1 : 1;
    const eyes = smooth(age / 0.21) * smooth((3.35 - age) / 0.26);
    const turn = stroke(age, 0.17, 1.22, 4.45);
    gaze.yaw += direction * (36 * eyes - 18 * turn);
    pose.head[1] += direction * 0.25 * turn;
    pose.chest[1] += direction * 0.078 * stroke(age, 0.47, 1.78, 4.58);
    pose.head[0] -= 0.028 * turn;
  } else if (gesture === "relax") {
    const release = stroke(age, 0.18, 1.65, 5.25);
    const arms = stroke(age, 0.55, 2.26, 5.36);
    pose.leftShoulder[2] -= 0.066 * release;
    pose.rightShoulder[2] += 0.048 * release;
    pose.chest[0] -= 0.053 * release;
    pose.head[0] -= 0.046 * arms;
    pose.leftLowerArm[2] -= 0.18 * arms;
    pose.rightLowerArm[2] += 0.14 * arms;
    pose.leftHand[0] += 0.12 * arms;
    pose.rightHand[0] += 0.09 * arms;
  } else if (gesture === "ponder") {
    const turn = stroke(age, 0.25, 1.52, 4.9);
    const lean = stroke(age, 0.57, 2.33, 4.98);
    gaze.yaw += 20 * stroke(age, 0, 0.29, 2.65);
    gaze.pitch += 11 * stroke(age, 0, 0.33, 2.3);
    pose.head[0] -= 0.082 * turn;
    pose.head[1] += 0.16 * turn;
    pose.head[2] -= 0.095 * turn;
    pose.chest[1] += 0.055 * lean;
    pose.leftLowerArm[2] -= 0.24 * lean;
    pose.leftShoulder[0] -= 0.04 * lean;
  } else if (gesture === "explain") {
    // Bring the palm forward, let it settle, then underline the phrase
    // with a smaller outward stroke. The elbow leads the fingers home.
    const present = stroke(age, 0.32, 1.54, 3.14);
    const accent = stroke(age, 1.94, 2.97, 4.61);
    const hand = smooth((age - 0.25) / 1.02) * smooth((5.05 - age) / 1.42);
    pose[`${side}Shoulder`][0] -= 0.078 * present + 0.04 * accent;
    pose.spine[2] += sign * (0.034 * present - 0.02 * accent);
    blend(`${side}UpperArm`, [
      -0.34 - 0.19 * present - 0.07 * accent,
      0,
      sign * (0.036 + 0.073 * accent),
    ]);
    blend(`${side}LowerArm`, [
      -0.46 - 0.12 * accent,
      0,
      sign * (1.57 + 0.4 * present + 0.19 * accent),
    ]);
    blend(
      `${side}Hand`,
      [1.27 + 0.09 * accent, sign * 0.08 * present, sign * 0.13 * accent],
      hand,
    );
    openness = hand * (0.74 + 0.25 * present + 0.16 * accent);
    pose.chest[1] -= sign * (0.07 * present + 0.032 * accent);
    pose.head[2] += sign * 0.054 * stroke(age, 0.2, 1.13, 3.36);
    pose.head[0] += 0.069 * stroke(age, 2.12, 2.91, 4.0);
    smile = Math.max(smile, 0.13 * weight);
  }
  if (gesture === "wave" || gesture === "explain") {
    // Lift in depth through the middle of the reach. A sideways sweep
    // takes the elbow and fingers to the edge of a narrow display.
    const arc = Math.sin(Math.PI * weight);
    pose[`${side}UpperArm`][0] -= (gesture === "wave" ? 1.33 : 0.6) * arc;
    pose[`${side}UpperArm`][2] -=
      sign * (gesture === "wave" ? 0.33 : 0.12) * arc;
    pose[`${side}LowerArm`][1] += sign * 0.12 * arc;
    transferWristRoll(pose, side);
  }
  const performance =
    gesture && isPerformance(gesture)
      ? applyPerformance(pose, gesture, age, side)
      : null;
  return {
    pose,
    smile,
    state,
    gesture,
    openness,
    gaze,
    face:
      performance?.face ??
      (gesture === "wave"
        ? { face: "appreciate", weight: weight * 0.6, wink: 0 }
        : null),
    hands: performance?.hands ?? null,
  };
}
