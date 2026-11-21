import assert from "node:assert/strict";
import test from "node:test";
import type { Vector3 } from "three";
import { aliceMotion, MOTION_BONES } from "../src/companion/alice-motion.ts";
import { palmNormal } from "../src/companion/hand-pose.ts";
import { JointMotion } from "../src/companion/motion-response.ts";
import {
  performances,
  type PerformanceName,
} from "../src/companion/performance-score.ts";
import { aliceRig, applyPose, filteredPose } from "./alice-rig-fixture.ts";

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
    let previous: Vector3 | undefined;
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
        filteredPose(rig, joints, motion, side, 1 / 30);
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

test("expressive arms stay articulated and three oblique claps close and reopen", () => {
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
        filteredPose(rig, joints, motion, side, 1 / 30);
        for (const [i, hand] of (["left", "right"] as const).entries()) {
          assert.ok(rig.position(hand + "Foot").distanceTo(rig.feet[i]) < 1e-8);
          const wrist = rig.position(hand + "Hand"),
            direction = rig
              .position(hand + "MiddleProximal")
              .sub(wrist)
              .normalize();
          const forearm = wrist
            .clone()
            .sub(rig.position(hand + "LowerArm"))
            .normalize();
          const palm = palmNormal(
            hand,
            wrist,
            rig.position(hand + "IndexProximal"),
            rig.position(hand + "MiddleProximal"),
            rig.position(hand + "LittleProximal"),
          );
          const wristRotation = rig.humanoid
            .getNormalizedBoneNode(hand + "Hand")!
            .quaternion.angleTo(rig.rest.get(hand + "Hand")!);
          assert.ok(
            wristRotation < 0.86 && direction.angleTo(forearm) < 0.94,
            `${name}: wrist folds at ${age}`,
          );
          assert.ok(
            Math.abs(forearm.dot(direction.clone().cross(palm).normalize())) <
              0.4,
            `${name}: wrist deviates sideways`,
          );
          if (
            hand === side &&
            age > 1.8 &&
            age < 2.4 &&
            (name === "giggle" || name === "gratefulBow")
          ) {
            const toward = rig
              .position(name === "giggle" ? "head" : "chest")
              .sub(wrist)
              .normalize();
            assert.ok(
              palm.dot(toward) > 0.6,
              `${name}: back of hand faces the character`,
            );
          }

          for (const finger of ["Thumb", "Index", "Middle", "Ring", "Little"]) {
            assert.ok(
              Math.abs(rig.position(hand + finger + "Distal").x) < 0.38,
              `${name} / ${side} / ${age}`,
            );
          }
        }
        if (name === "applause" && age > 1) {
          // This oblique clap meets along the finger pads. The two wrists
          // and knuckle roots deliberately stay apart because of the cuffs.
          const gap = rig
            .position("leftMiddleIntermediate")
            .distanceTo(rig.position("rightMiddleIntermediate"));
          if (!near && gap < 0.06) {
            contacts++;
            near = true;
          }
          if (gap > 0.12) near = false;
        }
      }
      if (name === "applause") assert.equal(contacts, 3);
    }
  }
});
