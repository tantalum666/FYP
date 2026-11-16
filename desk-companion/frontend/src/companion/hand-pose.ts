import * as THREE from "three";
import type { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";

/** Anatomical palm direction, derived from the rig rather than a wrist Euler sign. */
export function palmNormal(
  side: "left" | "right",
  wrist: THREE.Vector3,
  index: THREE.Vector3,
  middle: THREE.Vector3,
  little: THREE.Vector3,
) {
  const normal = middle.clone().sub(wrist).cross(index.clone().sub(little));
  return normal.multiplyScalar(side === "left" ? 1 : -1).normalize();
}

export function fingerCurlAxis(
  direction: THREE.Vector3,
  normal: THREE.Vector3,
) {
  return direction.clone().normalize().cross(normal).normalize();
}

type Finger = "Index" | "Middle" | "Ring" | "Little";
type Joint = "Proximal" | "Intermediate" | "Distal";
const FINGERS: Finger[] = ["Index", "Middle", "Ring", "Little"];
const JOINTS: Joint[] = ["Proximal", "Intermediate", "Distal"];

/** Small finger relaxation follows each palm's native flexion plane. */
export class HandPose {
  private joints: Array<{
    node: THREE.Object3D;
    rest: THREE.Quaternion;
    axis: THREE.Vector3;
    side: "left" | "right";
    finger: number;
    joint: number;
  }> = [];
  private offset = new THREE.Quaternion();
  private target = new THREE.Quaternion();

  constructor(vrm: Pick<VRM, "humanoid">) {
    const bone = (name: string) =>
      vrm.humanoid.getNormalizedBoneNode(name as VRMHumanBoneName);
    const position = (node: THREE.Object3D) =>
      node.getWorldPosition(new THREE.Vector3());
    for (const side of ["left", "right"] as const) {
      const wrist = bone(`${side}Hand`),
        index = bone(`${side}IndexProximal`),
        middle = bone(`${side}MiddleProximal`),
        little = bone(`${side}LittleProximal`);
      if (!wrist || !index || !middle || !little) continue;
      const normal = palmNormal(
        side,
        position(wrist),
        position(index),
        position(middle),
        position(little),
      );
      if (normal.lengthSq() < 0.5) continue;
      for (const [fingerIndex, finger] of FINGERS.entries()) {
        for (const [jointIndex, joint] of JOINTS.entries()) {
          const node = bone(`${side}${finger}${joint}`);
          const next = bone(
            `${side}${finger}${JOINTS[Math.min(2, jointIndex + 1)]}`,
          );
          const previous = bone(
            `${side}${finger}${JOINTS[Math.max(0, jointIndex - 1)]}`,
          );
          if (!node || !next || !previous) continue;
          const direction =
            jointIndex === 2
              ? position(node).sub(position(previous))
              : position(next).sub(position(node));
          const axis = fingerCurlAxis(direction, normal).applyQuaternion(
            node.getWorldQuaternion(new THREE.Quaternion()).invert(),
          );
          if (axis.lengthSq() < 0.5) continue;
          this.joints.push({
            node,
            rest: node.quaternion.clone(),
            axis,
            side,
            finger: fingerIndex,
            joint: jointIndex,
          });
        }
      }
    }
  }

  update(delta: number, wavingSide: "left" | "right" | null, openness: number) {
    const blend = 1 - Math.exp(-7 * Math.max(0, delta));
    for (const item of this.joints) {
      const open =
        wavingSide === item.side ? Math.max(0, Math.min(1, openness)) : 0;
      const relaxed = 0.12 + item.finger * 0.035;
      const greeting = 0.025 + item.finger * 0.018;
      const curl =
        (relaxed * (1 - open) + greeting * open) * [0.7, 0.9, 0.55][item.joint];
      this.offset.setFromAxisAngle(item.axis, curl);
      this.target.copy(item.rest).multiply(this.offset);
      item.node.quaternion.slerp(this.target, blend);
    }
  }
}

export function relaxArms(vrm: Pick<VRM, "humanoid">) {
  for (const side of ["left", "right"] as const) {
    const upper = vrm.humanoid.getNormalizedBoneNode(`${side}UpperArm`);
    const lower = vrm.humanoid.getNormalizedBoneNode(`${side}LowerArm`);
    if (!upper || !lower || !upper.parent) continue;
    const shoulder = upper.getWorldPosition(new THREE.Vector3());
    const elbow = lower.getWorldPosition(new THREE.Vector3());
    const parentRotation = upper.parent
      .getWorldQuaternion(new THREE.Quaternion())
      .invert();
    const rest = elbow
      .sub(shoulder)
      .normalize()
      .applyQuaternion(parentRotation);
    const outward = Math.sign(shoulder.x) || (side === "left" ? 1 : -1);
    const down = new THREE.Vector3(outward * 0.2, -1, 0.03)
      .normalize()
      .applyQuaternion(parentRotation);
    upper.quaternion.premultiply(
      new THREE.Quaternion().setFromUnitVectors(rest, down),
    );
  }
}
