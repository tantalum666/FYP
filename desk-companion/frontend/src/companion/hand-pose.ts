import * as THREE from "three";
import {
  fingers,
  fingerAngle,
  followHandShape,
  type Finger,
} from "./finger-articulation.ts";
import { thumbPoses } from "./thumb-opposition.ts";
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

type Side = "left" | "right";
type Hinge = {
  node: THREE.Object3D;
  rest: THREE.Quaternion;
  bend: THREE.Vector3;
};
type Digit = {
  side: Side;
  name: Finger;
  shape: number;
  joints: Hinge[];
  fan: THREE.Vector3;
  cup: THREE.Vector3;
  knuckle: {
    node: THREE.Object3D;
    rest: THREE.Vector3;
    axis: THREE.Vector3;
  } | null;
};
type Thumb = {
  side: Side;
  shape: number;
  nodes: readonly [THREE.Object3D, THREE.Object3D, THREE.Object3D];
  poses: ReturnType<typeof thumbPoses>;
};
const location = (node: THREE.Object3D) =>
  node.getWorldPosition(new THREE.Vector3());
const localAxis = (axis: THREE.Vector3, node: THREE.Object3D) =>
  axis
    .clone()
    .applyQuaternion(node.getWorldQuaternion(new THREE.Quaternion()).invert());

/** Articulate the existing finger bones from the model's own palm plane. */
export class HandPose {
  private digits: Digit[] = [];
  private thumbs: Thumb[] = [];
  private offset = new THREE.Quaternion();

  constructor(vrm: Pick<VRM, "humanoid">) {
    const { humanoid } = vrm;
    const bone = (name: string) =>
      humanoid.getNormalizedBoneNode(name as VRMHumanBoneName);
    for (const side of ["left", "right"] as const) {
      const wrist = bone(side + "Hand"),
        index = bone(side + "IndexProximal"),
        middle = bone(side + "MiddleProximal"),
        little = bone(side + "LittleProximal");
      if (!wrist || !index || !middle || !little) continue;
      const origin = location(wrist),
        center = location(middle);
      const normal = palmNormal(
        side,
        origin,
        location(index),
        center,
        location(little),
      );
      if (normal.lengthSq() < 0.5) continue;
      const lengthwise = center.clone().sub(origin).normalize();
      for (const name of Object.keys(fingers) as Finger[]) {
        const base = bone(side + name + "Proximal"),
          mid = bone(side + name + "Intermediate"),
          tip = bone(side + name + "Distal");
        if (!base || !mid || !tip) continue;
        const first = location(mid).sub(location(base)),
          last = location(tip).sub(location(mid));
        if (first.lengthSq() < 1e-9 || last.lengthSq() < 1e-9) continue;
        const outside = location(base).sub(center);
        const fanSign = Math.sign(first.clone().cross(outside).dot(normal));
        const cupSign = Math.sign(
          lengthwise.clone().cross(outside).dot(normal),
        );
        const cup = lengthwise.clone().multiplyScalar(cupSign);
        const raw = humanoid.getRawBoneNode(`${side}${name}Proximal`),
          rawHand = humanoid.getRawBoneNode(`${side}Hand`);
        // On Alice, the knuckles attach directly to the hand. Rotate the
        // ulnar knuckles about the palm's long axis to form a shallow arch.
        const knuckle =
          raw && rawHand && raw.parent === rawHand && fingers[name].cup[0] > 0
            ? {
                node: raw,
                rest: raw.position.clone(),
                axis: localAxis(cup, rawHand),
              }
            : null;
        const joints = [base, mid, tip].map((node, i) => ({
          node,
          rest: node.quaternion.clone(),
          bend: localAxis(fingerCurlAxis(i === 0 ? first : last, normal), node),
        }));
        this.digits.push({
          side,
          name,
          shape: 0,
          joints,
          fan: localAxis(normal.clone().multiplyScalar(fanSign), base),
          cup: localAxis(cup, base),
          knuckle,
        });
      }
      const base = bone(side + "ThumbMetacarpal"),
        mid = bone(side + "ThumbProximal"),
        tip = bone(side + "ThumbDistal");
      if (!base || !mid || !tip) continue;
      if (
        location(mid).distanceToSquared(location(base)) < 1e-8 ||
        location(tip).distanceToSquared(location(mid)) < 1e-8
      )
        continue;
      const nodes = [base, mid, tip] as const;
      this.thumbs.push({
        side,
        shape: 0,
        nodes,
        poses: thumbPoses(
          nodes,
          origin,
          center,
          location(index),
          location(little),
          normal,
        ),
      });
    }
    this.update(0, null, 0);
  }

  update(
    delta: number,
    wavingSide: Side | null,
    openness: number,
    shapes?: Partial<Record<Side, number>> | null,
  ) {
    const target = (side: Side) =>
      THREE.MathUtils.clamp(
        shapes?.[side] ?? (wavingSide === side ? openness : 0),
        -1,
        1,
      );
    for (const digit of this.digits) {
      const profile = fingers[digit.name];
      const s = (digit.shape = followHandShape(
        digit.shape,
        target(digit.side),
        delta,
        profile.openRate,
        profile.closeRate,
      ));
      const cup = fingerAngle(s, ...profile.cup),
        fan = fingerAngle(s, ...profile.spread);
      if (digit.knuckle)
        digit.knuckle.node.position
          .copy(digit.knuckle.rest)
          .applyAxisAngle(digit.knuckle.axis, cup);
      digit.joints.forEach(({ node, rest, bend }, i) => {
        node.quaternion.copy(rest);
        if (i === 0) {
          if (cup)
            node.quaternion.multiply(
              this.offset.setFromAxisAngle(digit.cup, cup),
            );
          if (fan)
            node.quaternion.multiply(
              this.offset.setFromAxisAngle(digit.fan, fan),
            );
        }
        const curl = fingerAngle(
          s,
          profile.rest[i],
          profile.open[i],
          profile.grip[i],
        );
        node.quaternion.multiply(this.offset.setFromAxisAngle(bend, curl));
      });
    }
    for (const thumb of this.thumbs) {
      const s = (thumb.shape = followHandShape(
        thumb.shape,
        target(thumb.side),
        delta,
        13,
        5.2,
      ));
      // Move around the radial edge before opposing the folded fingers.
      const { rest, open, clear, grip } = thumb.poses;
      let from = rest,
        to = open,
        amount = s;
      if (s < 0) {
        const closing = -s,
          wrapStart = 0.64;
        if (closing <= wrapStart) {
          to = clear;
          amount = closing / wrapStart;
        } else {
          from = clear;
          to = grip;
          amount = (closing - wrapStart) / (1 - wrapStart);
        }
      }
      thumb.nodes.forEach((node, i) =>
        node.quaternion.copy(from[i]).slerp(to[i], amount),
      );
    }
  }
}

/** Reference orientation used to author gesture offsets on normalized VRM bones. */
export function setArmReference(vrm: Pick<VRM, "humanoid">) {
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
    const down = new THREE.Vector3(outward * 0.53, -1, 0.27)
      .normalize()
      .applyQuaternion(parentRotation);
    upper.quaternion.premultiply(
      new THREE.Quaternion().setFromUnitVectors(rest, down),
    );
  }
}

// The original inspection scripts import this name for the gesture reference.
export { setArmReference as relaxArms };
