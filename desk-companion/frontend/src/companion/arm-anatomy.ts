import { Euler, Quaternion, Vector3, MathUtils } from "three";
import type { armLandmarks } from "./arm-landmarks.ts";
import type { MotionPose } from "./alice-motion.ts";

type Landmark = (typeof armLandmarks)[keyof typeof armLandmarks];
type Side = "left" | "right";
type Angles = [number, number, number];

// Normalized left-arm axes measured from Alice's elbow, wrist and knuckles.
// Mirroring an axial rotation keeps X and negates Y and Z.
const hinge = new Vector3(0, -0.99, -0.141).normalize();
const forearm = new Vector3(-1, 0, -0.00175).normalize();
const acrossPalm = new Vector3(-0.02935, 0.01327, 0.99948).normalize();
const palmNormal = new Vector3(-0.11081, -0.99379, 0.00994).normalize();
const shoulder = new Quaternion(),
  target = new Quaternion(),
  second = new Quaternion(),
  base = new Quaternion();
const euler = new Euler(),
  identity = new Quaternion();

function put(angles: Angles, q: Quaternion) {
  euler.setFromQuaternion(q);
  angles[0] = euler.x;
  angles[1] = euler.y;
  angles[2] = euler.z;
}
function compose(angles: Angles, goal: Quaternion, side: Side, weight: number) {
  if (side === "right") {
    goal.y = -goal.y;
    goal.z = -goal.z;
  }
  base.setFromEuler(euler.set(...angles)).slerp(identity, weight);
  put(angles, base.multiply(goal));
}

export function applyArmLandmarks(
  pose: MotionPose,
  side: Side,
  from: Landmark,
  to: Landmark,
  t: number,
  weight: number,
) {
  if (weight === 0) return;
  const angle = (a: number, b: number) =>
    MathUtils.degToRad(MathUtils.lerp(a, b, t) * weight);
  shoulder.setFromEuler(
    euler.set(
      angle(from.upper[0], to.upper[0]),
      angle(from.upper[1], to.upper[1]),
      angle(from.upper[2], to.upper[2]),
    ),
  );
  compose(pose[`${side}UpperArm`], shoulder, side, weight);
  target
    .setFromAxisAngle(hinge, angle(from.elbow[0], to.elbow[0]))
    .multiply(
      second.setFromAxisAngle(forearm, angle(from.elbow[1], to.elbow[1])),
    );
  compose(pose[`${side}LowerArm`], target, side, weight);
  target
    .setFromAxisAngle(acrossPalm, angle(from.wrist[0], to.wrist[0]))
    .multiply(
      second.setFromAxisAngle(palmNormal, angle(from.wrist[1], to.wrist[1])),
    );
  compose(pose[`${side}Hand`], target, side, weight);
}

/** Keep the existing greeting's palm direction and fingertip path, but turn
 * the forearm around its own long axis instead of twisting the hand at the cuff. */
export function transferWristRoll(pose: MotionPose, side: Side) {
  const lower = pose[`${side}LowerArm`],
    hand = pose[`${side}Hand`];
  const axisZ = side === "left" ? forearm.z : -forearm.z;
  target.setFromEuler(euler.set(...hand));
  const projection = target.x * forearm.x + target.z * axisZ;
  second
    .set(forearm.x * projection, 0, axisZ * projection, target.w)
    .normalize();
  put(lower, base.setFromEuler(euler.set(...lower)).multiply(second));
  put(hand, second.invert().multiply(target));
}
