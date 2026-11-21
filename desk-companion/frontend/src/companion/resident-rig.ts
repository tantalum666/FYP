import { Euler, Quaternion, type Object3D } from "three";
import type { VRM } from "@pixiv/three-vrm";
import { aliceMotion, MOTION_BONES, type MotionBone } from "./alice-motion.ts";
import { HandPose, setArmReference } from "./hand-pose.ts";
import { JointMotion } from "./motion-response.ts";

export function bindResidentRig(humanoid: VRM["humanoid"], scene: Object3D) {
  setArmReference({ humanoid });
  humanoid.update();
  scene.updateMatrixWorld(true);
  const bones = new Map<
    MotionBone,
    { node: Object3D; rest: Quaternion; response: JointMotion }
  >();
  const hands = new HandPose({ humanoid }),
    initial = aliceMotion(0).pose,
    euler = new Euler(),
    offset = new Quaternion();
  for (const name of MOTION_BONES) {
    const node = humanoid.getNormalizedBoneNode(name);
    if (!node) continue;
    const rest = node.quaternion.clone();
    bones.set(name, {
      node,
      rest,
      response: new JointMotion(name, initial[name]),
    });
    node.quaternion.multiply(offset.setFromEuler(euler.set(...initial[name])));
  }
  humanoid.update();
  scene.updateMatrixWorld(true);
  return { bones, hands };
}
