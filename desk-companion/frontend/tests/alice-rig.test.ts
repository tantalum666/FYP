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
import { JointMotion } from "../src/companion/motion-response.ts";
import {
  performances,
  type PerformanceName,
} from "../src/companion/performance-score.ts";

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

function applyPose(
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

for (const side of ["left", "right"] as const)
  test(`${side} greeting shows its palm, thumb toward the face, on Alice's actual rig`, () => {
    const rig = aliceRig();
    for (const age of [1.8, 2.15, 2.65, 3.0]) {
      const motion = aliceMotion(age, {
        gesture: "wave",
        gestureAt: 0,
        waveSide: side,
      });
      applyPose(rig, motion, side);
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

for (const side of ["left", "right"] as const)
  test(`${side} explanation stays in front of the body and inside the phone hand envelope`, () => {
    const rig = aliceRig();
    let travel = 0;
    let previous: THREE.Vector3 | undefined;
    for (let frame = 90; frame <= 210; frame++) {
      const age = frame / 60;
      const motion = aliceMotion(age, {
        gesture: "explain",
        gestureAt: 0,
        waveSide: side,
      });
      applyPose(rig, motion, side);
      const wrist = rig.position(side + "Hand");
      if (previous) travel += previous.distanceTo(wrist);
      previous = wrist;
      const palm = palmNormal(
        side,
        wrist,
        rig.position(side + "IndexProximal"),
        rig.position(side + "MiddleProximal"),
        rig.position(side + "LittleProximal"),
      );
      assert.ok(
        palm.z > 0.6,
        `explanation shows back of hand: ${palm.toArray()}`,
      );
      assert.ok(
        wrist.z > 0.08 && Math.abs(wrist.x) > 0.17,
        "hand falls into torso",
      );
      for (const finger of ["Index", "Middle", "Ring", "Little"])
        assert.ok(
          Math.abs(rig.position(side + finger + "Distal").x) < 0.38,
          "fingers exceed compact phone pose",
        );
      for (const [index, name] of ["leftFoot", "rightFoot"].entries())
        assert.ok(rig.position(name).distanceTo(rig.feet[index]) < 1e-8);
    }
    // During the middle two seconds a held pose only moved with breathing.
    assert.ok(travel > 0.035 && travel < 0.15, `wrist path: ${travel} m`);
  });

test("the moving fingertips stay inside the phone envelope throughout the lift and return", () => {
  for (const side of ["left", "right"] as const) {
    for (const gesture of ["wave", "explain"] as const) {
      const rig = aliceRig();
      const joints = MOTION_BONES.map((bone) => new JointMotion(bone));
      for (let frame = 0; frame < 220; frame++) {
        const time = frame / 30;
        const motion = aliceMotion(time, {
          gesture,
          gestureAt: 1,
          waveSide: side,
        });
        MOTION_BONES.forEach((bone, i) => {
          const [x, y, z] = joints[i].update(motion.pose[bone], 1 / 30);
          motion.pose[bone] = [x, y, z];
        });
        applyPose(rig, motion, side, 1 / 30);
        for (const finger of ["Thumb", "Index", "Middle", "Ring", "Little"]) {
          const tip = rig.position(side + finger + "Distal");
          assert.ok(
            Math.abs(tip.x) < 0.38,
            `${side} ${gesture}: fingertip at ${tip.x} m, ${time} s`,
          );
        }
      }
    }
  }
});

test("expressive scores keep both hands framed and the three applause beats meet", () => {
  for (const name of Object.keys(performances) as PerformanceName[]) {
    for (const side of ["left", "right"] as const) {
      const rig = aliceRig(),
        joints = MOTION_BONES.map((bone) => new JointMotion(bone));
      let contacts = 0,
        near = false;
      for (
        let frame = 0;
        frame < (performances[name].duration + 2) * 30;
        frame++
      ) {
        const age = frame / 30 - 1;
        const motion = aliceMotion(frame / 30, {
          gesture: name,
          gestureAt: 1,
          waveSide: side,
        });
        MOTION_BONES.forEach((bone, i) => {
          const [x, y, z] = joints[i].update(
            motion.pose[bone],
            1 / 30,
            name === "applause",
          );
          motion.pose[bone] = [x, y, z];
        });
        applyPose(rig, motion, side, 1 / 30);
        for (const [i, hand] of (["left", "right"] as const).entries()) {
          assert.ok(rig.position(hand + "Foot").distanceTo(rig.feet[i]) < 1e-8);
          for (const finger of ["Thumb", "Index", "Middle", "Ring", "Little"]) {
            assert.ok(
              Math.abs(rig.position(hand + finger + "Distal").x) < 0.38,
              `${name} / ${side} / ${age}`,
            );
          }
        }
        if (name === "applause" && age > 1) {
          const gap = rig
            .position("leftMiddleProximal")
            .distanceTo(rig.position("rightMiddleProximal"));
          if (!near && gap < 0.052) {
            contacts++;
            near = true;
          }
          if (gap > 0.14) near = false;
        }
      }
      if (name === "applause") assert.equal(contacts, 3);
    }
  }
});
