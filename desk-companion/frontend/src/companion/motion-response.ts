import type { MotionBone } from "./alice-motion.ts";
import { Euler, Quaternion } from "three";

/** A local joint offset and its velocity survive changes of gesture or state. */
export class JointMotion {
  readonly angles = [0, 0, 0];
  private velocity = [0, 0, 0];
  private rotation = [0, 0, 0];
  private targetVector = [0, 0, 0];
  private q = new Quaternion();
  private euler = new Euler();

  private readonly rate: number;
  private readonly handChain: boolean;

  constructor(bone: MotionBone) {
    this.rate = bone.endsWith("Arm") ? 8 : 13;
    this.handChain = bone.endsWith("Arm") || bone.endsWith("Hand");
  }

  update(target: readonly number[], seconds: number, trackingContact = false) {
    // Euler triples can change by half a turn while describing the same pose.
    // Track a continuous rotation vector so that crossing that seam never
    // sends the elbow or palm on a detour through the body.
    const q = this.q.setFromEuler(
      this.euler.set(target[0], target[1], target[2]),
    );
    const sin = Math.hypot(q.x, q.y, q.z);
    const angle = 2 * Math.atan2(sin, q.w);
    const along =
      sin > 1e-8
        ? (this.rotation[0] * q.x +
            this.rotation[1] * q.y +
            this.rotation[2] * q.z) /
          sin
        : 0;
    const scale =
      sin > 1e-8
        ? (angle + 2 * Math.PI * Math.round((along - angle) / (2 * Math.PI))) /
          sin
        : 0;
    this.targetVector[0] = q.x * scale;
    this.targetVector[1] = q.y * scale;
    this.targetVector[2] = q.z * scale;
    const rate = trackingContact && this.handChain ? 21 : this.rate;
    const decay = Math.exp(-rate * seconds);
    for (let axis = 0; axis < 3; axis++) {
      const goal = this.targetVector[axis];
      const distance = this.rotation[axis] - goal;
      const change = this.velocity[axis] + rate * distance;
      this.rotation[axis] = goal + (distance + change * seconds) * decay;
      this.velocity[axis] =
        (this.velocity[axis] - rate * change * seconds) * decay;
    }
    const [x, y, z] = this.rotation,
      length = Math.hypot(x, y, z),
      half = length / 2;
    const factor = length > 1e-8 ? Math.sin(half) / length : 0.5;
    this.euler.setFromQuaternion(
      q.set(x * factor, y * factor, z * factor, Math.cos(half)),
    );
    this.angles[0] = this.euler.x;
    this.angles[1] = this.euler.y;
    this.angles[2] = this.euler.z;
    return this.angles;
  }
}
