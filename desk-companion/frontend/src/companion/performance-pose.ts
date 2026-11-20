import { armLandmarks } from "./arm-landmarks.ts";
import {
  performances,
  type ArmKey,
  type Face,
  type Performance,
  type PerformanceName,
} from "./performance-score.ts";
import type { MotionPose } from "./alice-motion.ts";

export type Side = "left" | "right";
export type HandShapes = Record<Side, number>;
export type FaceCue = {
  face: Face;
  weight: number;
  wink: number;
  eyelids?: number;
};
const smooth = (value: number) => {
  const x = Math.max(0, Math.min(1, value));
  return x * x * (3 - 2 * x);
};
function segment<T extends readonly [number, ...unknown[]]>(
  track: readonly T[],
  age: number,
): [T, T, number] {
  let first = track[0];
  for (const next of track.slice(1)) {
    if (age <= next[0])
      return [first, next, smooth((age - first[0]) / (next[0] - first[0]))];
    first = next;
  }
  return [first, first, 0];
}
const mix = (a: number, b: number, t: number) => a + (b - a) * t;

function arm(
  pose: MotionPose,
  side: Side,
  keys: readonly ArmKey[],
  age: number,
) {
  const [from, to, t] = segment(keys, age);
  const a = from[1] === "rest" ? null : armLandmarks[from[1]];
  const b = to[1] === "rest" ? null : armLandmarks[to[1]];
  for (const [bone, part] of [
    ["UpperArm", "upper"],
    ["LowerArm", "lower"],
    ["Hand", "wrist"],
  ] as const) {
    const angles = pose[`${side}${bone}`];
    for (let axis = 0; axis < 3; axis++) {
      const mirror = axis === 0 || side === "left" ? 1 : -1;
      angles[axis] = mix(
        a ? a[part][axis] * mirror : angles[axis],
        b ? b[part][axis] * mirror : angles[axis],
        t,
      );
    }
  }
  if (!!a !== !!b) {
    // Bend forward on the way up and down. Linear interpolation between
    // these two rotations otherwise swings a long sleeve off the phone.
    const arc = Math.sin(t * Math.PI),
      inward = side === "left" ? 1 : -1;
    pose[`${side}UpperArm`][0] -= 0.85 * arc;
    pose[`${side}UpperArm`][2] += inward * 0.19 * arc;
    pose[`${side}LowerArm`][1] -= inward * 0.12 * arc;
  }
  return mix(a?.fingers ?? 0, b?.fingers ?? 0, t);
}

export function isPerformance(name: string): name is PerformanceName {
  return Object.hasOwn(performances, name);
}

/** Sample the authored score in the resident renderer's time, in local bone space. */
export function applyPerformance(
  pose: MotionPose,
  name: PerformanceName,
  age: number,
  primary: Side,
) {
  const score: Performance = performances[name],
    other = primary === "left" ? "right" : "left";
  const hands: HandShapes = { left: 0, right: 0 };
  hands[primary] = arm(pose, primary, score.primary, age);
  if (score.other)
    hands[other] = arm(
      pose,
      other,
      score.other === "mirror" ? score.primary : score.other,
      age,
    );
  const [a, b, t] = segment(score.body, age);
  const bend = mix(a[1], b[1], t),
    turn = mix(a[2], b[2], t),
    tilt = mix(a[3], b[3], t),
    nod = mix(a[4], b[4], t);
  const side = primary === "left" ? 1 : -1;
  pose.spine[0] -= bend * 0.53;
  pose.chest[0] -= bend * 0.47;
  pose.spine[2] += tilt * side * 0.23;
  pose.chest[1] += turn * side * 0.25;
  pose.neck[2] += tilt * side * 0.3;
  pose.head[2] += tilt * side * 0.65;
  pose.head[0] -= nod;
  pose.head[1] += turn * side * 0.8;
  const face: FaceCue = {
    face: score.face,
    eyelids:
      name === "gratefulBow"
        ? 0.82 * smooth((age - 0.98) / 0.57) * smooth((3.12 - age) / 0.68)
        : 0,
    weight:
      (score.faceStrength ?? 1) *
      smooth(age / (score.face === "surprised" ? 0.26 : 0.57)) *
      smooth((score.duration - age) / 1.16),
    wink: score.wink
      ? smooth((age - 0.86) / 0.18) * smooth((1.66 - age) / 0.22)
      : 0,
  };
  return { hands, face };
}
