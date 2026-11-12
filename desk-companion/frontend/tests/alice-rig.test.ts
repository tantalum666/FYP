import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import {
  VRMHumanoid,
  type VRMHumanBones,
  type VRMHumanBoneName,
} from "@pixiv/three-vrm";
import { aliceMotion, MOTION_BONES } from "../src/companion/alice-motion.ts";
import { HandPose, palmNormal, relaxArms } from "../src/companion/hand-pose.ts";

function aliceRig() {
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
  return { scene, humanoid, hands, rest, position, feet };
}

for (const side of ["left", "right"] as const)
  test(`${side} greeting shows its palm, thumb toward the face, on Alice's actual rig`, () => {
    const rig = aliceRig();
    for (const age of [1.8, 2.15, 2.65, 3.0]) {
      const motion = aliceMotion(age, {
        gesture: "wave",
        gestureAt: 0,
        waveSide: side,
      });
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
      rig.hands.update(1, side, motion.openness);
      rig.humanoid.update();
      rig.scene.updateMatrixWorld(true);
      const wrist = rig.position(side + "Hand");
      const normal = palmNormal(
        side,
        wrist,
        rig.position(side + "IndexProximal"),
        rig.position(side + "MiddleProximal"),
        rig.position(side + "LittleProximal"),
      );
      assert.ok(
        normal.z > 0.8,
        `palm points away at ${age}: ${normal.toArray()}`,
      );
      assert.ok(
        Math.sign(wrist.x) * (rig.position(side + "ThumbDistal").x - wrist.x) <
          0,
        "thumb points away from face",
      );
      for (const [index, name] of ["leftFoot", "rightFoot"].entries())
        assert.ok(rig.position(name).distanceTo(rig.feet[index]) < 1e-8);
    }
  });
