import { readFileSync } from "node:fs";
import * as THREE from "three";
import {
  VRMHumanoid,
  type VRMHumanBones,
  type VRMHumanBoneName,
} from "@pixiv/three-vrm";
import { aliceMotion, MOTION_BONES } from "../src/companion/alice-motion.ts";
import { HandPose, relaxArms } from "../src/companion/hand-pose.ts";
import { JointMotion } from "../src/companion/motion-response.ts";

export function aliceRig() {
  // The shipped model's real joint hierarchy, without texture/mesh loading or a GPU.
  const bytes = readFileSync(
    new URL("../public/avatars/alice/alice-ready.vrm", import.meta.url),
  );
  const source = JSON.parse(
    bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString(),
  );
  const nodes = source.nodes.map((definition: any) => {
    const node = new THREE.Object3D();
    node.name = definition.name ?? "";
    if (definition.matrix)
      new THREE.Matrix4()
        .fromArray(definition.matrix)
        .decompose(node.position, node.quaternion, node.scale);
    else {
      if (definition.translation)
        node.position.fromArray(definition.translation);
      if (definition.rotation) node.quaternion.fromArray(definition.rotation);
      if (definition.scale) node.scale.fromArray(definition.scale);
    }
    return node;
  });
  source.nodes.forEach((definition: any, index: number) => {
    for (const child of definition.children ?? [])
      nodes[index].add(nodes[child]);
  });
  const scene = new THREE.Group();
  for (const node of source.scenes[source.scene ?? 0].nodes)
    scene.add(nodes[node]);
  scene.updateMatrixWorld(true);
  const bones: Record<string, { node: THREE.Object3D }> = {};
  for (const entry of source.extensions.VRM.humanoid.humanBones) {
    const name = entry.bone
      .replace("ThumbProximal", "ThumbMetacarpal")
      .replace("ThumbIntermediate", "ThumbProximal");
    bones[name] = { node: nodes[entry.node] };
  }
  const humanoid = new VRMHumanoid(bones as VRMHumanBones);
  scene.add(humanoid.normalizedHumanBonesRoot);
  scene.rotation.y = Math.PI; // Same VRM0-facing correction as VrmViewer.
  scene.updateMatrixWorld(true);
  relaxArms({ humanoid });
  humanoid.update();
  scene.updateMatrixWorld(true);
  const hands = new HandPose({ humanoid });
  const rest = new Map(
    MOTION_BONES.map((name) => [
      name,
      humanoid.getNormalizedBoneNode(name)!.quaternion.clone(),
    ]),
  );
  const position = (name: string) =>
    humanoid
      .getRawBoneNode(name as VRMHumanBoneName)!
      .getWorldPosition(new THREE.Vector3());
  const feet = ["leftFoot", "rightFoot"].map(position);
  return {
    scene,
    humanoid,
    hands,
    rest,
    position,
    feet,
    nodes: nodes as THREE.Object3D[],
    source,
  };
}

export function applyPose(
  rig: ReturnType<typeof aliceRig>,
  motion: ReturnType<typeof aliceMotion>,
  side: "left" | "right",
  elapsed = 1,
) {
  for (const name of MOTION_BONES) {
    const node = rig.humanoid.getNormalizedBoneNode(name)!;
    node.quaternion
      .copy(rig.rest.get(name)!)
      .multiply(
        new THREE.Quaternion().setFromEuler(
          new THREE.Euler(...motion.pose[name]),
        ),
      );
  }
  rig.hands.update(elapsed, side, motion.openness, motion.hands);
  rig.humanoid.update();
  rig.scene.updateMatrixWorld(true);
}

/** Advance the same filters and finger pose as the resident renderer before measuring. */
export function filteredPose(
  rig: ReturnType<typeof aliceRig>,
  joints: JointMotion[],
  motion: ReturnType<typeof aliceMotion>,
  side: "left" | "right",
  dt: number,
) {
  MOTION_BONES.forEach((bone, i) => {
    const [x, y, z] = joints[i].update(
      motion.pose[bone],
      dt,
      motion.gesture === "applause",
    );
    motion.pose[bone] = [x, y, z];
  });
  applyPose(rig, motion, side, dt);
}
