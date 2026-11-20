import type { MotionBone } from "./alice-motion.ts";

/** A local joint offset and its velocity survive changes of gesture or state. */
export class JointMotion {
  readonly angles = [0, 0, 0];
  private velocity = [0, 0, 0];

  private readonly rate: number;
  private readonly handChain: boolean;

  constructor(bone: MotionBone) {
    this.rate = bone.endsWith("Arm") ? 8 : 13;
    this.handChain = bone.endsWith("Arm") || bone.endsWith("Hand");
  }

  update(target: readonly number[], seconds: number, trackingContact = false) {
    // Exact critically damped response to this frame's target, in radians.
    const rate = trackingContact && this.handChain ? 21 : this.rate;
    const decay = Math.exp(-rate * seconds);
    for (let axis = 0; axis < 3; axis++) {
      const distance = this.angles[axis] - target[axis];
      const change = this.velocity[axis] + rate * distance;
      this.angles[axis] = target[axis] + (distance + change * seconds) * decay;
      this.velocity[axis] =
        (this.velocity[axis] - rate * change * seconds) * decay;
    }
    return this.angles;
  }
}
