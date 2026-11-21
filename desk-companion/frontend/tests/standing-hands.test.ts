import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import fit from "../src/companion/uniform-rest.json" with { type: "json" };
import { MathUtils } from "three";
import { aliceRig, filteredPose } from "./alice-rig-fixture.ts";
import { aliceMotion } from "../src/companion/alice-motion.ts";
import { palmNormal } from "../src/companion/hand-pose.ts";

type Rig = ReturnType<typeof aliceRig>;
type Side = "left" | "right";
const degrees = MathUtils.radToDeg;
function arm(rig: Rig, side: Side) {
  const shoulder = rig.position(side + "UpperArm"),
    elbow = rig.position(side + "LowerArm"),
    wrist = rig.position(side + "Hand");
  const forearm = wrist.clone().sub(elbow),
    upper = elbow.clone().sub(shoulder);
  const palm = palmNormal(
    side,
    wrist,
    rig.position(side + "IndexProximal"),
    rig.position(side + "MiddleProximal"),
    rig.position(side + "LittleProximal"),
  );
  return {
    front: degrees(Math.atan2(Math.abs(upper.x), -upper.y)),
    profile: degrees(Math.atan2(Math.abs(upper.z), -upper.y)),
    wristFront: degrees(
      Math.atan2(Math.abs(wrist.x - shoulder.x), shoulder.y - wrist.y),
    ),
    elbow: degrees(upper.angleTo(forearm)),
    palmIn: -Math.sign(shoulder.x) * palm.x,
  };
}
function hand(rig: Rig, side: Side) {
  const p = (n: string) => rig.position(side + n);
  const wrist = p("Hand"),
    index = p("IndexProximal"),
    middle = p("MiddleProximal"),
    little = p("LittleProximal");
  const normal = palmNormal(side, wrist, index, middle, little);
  const bends = ["Index", "Middle", "Ring", "Little"].map((d) =>
    degrees(
      p(d + "Intermediate")
        .sub(p(d + "Proximal"))
        .angleTo(p(d + "Distal").sub(p(d + "Intermediate"))),
    ),
  );
  const radial = index.clone().sub(little).normalize();
  return {
    bends,
    normal,
    thumbPad: p("ThumbDistal"),
    thumbAcross: p("ThumbDistal").sub(p("ThumbProximal")).dot(radial),
    thumbDepth: p("ThumbDistal").sub(wrist).dot(normal),
    knuckle: little.clone().sub(wrist),
  };
}
function fingersAt(rig: Rig, side: Side, shape: number, dt = 4) {
  rig.hands.update(dt, side, 0, { [side]: shape });
  rig.humanoid.update();
  rig.scene.updateMatrixWorld(true);
  return hand(rig, side);
}

test("the resident arm hangs close on the first frame, while waiting and after a gesture returns", () => {
  for (const side of ["left", "right"] as const) {
    const rig = aliceRig();
    const check = () => {
      const a = arm(rig, side);
      assert.ok(a.front > 3 && a.front < 13, JSON.stringify(a));
      assert.ok(a.profile < 10 && a.wristFront < 17, JSON.stringify(a));
      assert.ok(
        a.elbow > 10 && a.elbow < 32 && a.palmIn > 0.76,
        JSON.stringify(a),
      );
    };
    check();
    for (let frame = 0; frame < 660; frame++) {
      const time = frame / 30,
        motion = aliceMotion(time, {
          state: frame < 440 ? "idle" : "listening",
          gesture: "wave",
          gestureAt: 6,
          waveSide: side,
        });
      filteredPose(rig, rig.joints, motion, side, 1 / 30);
      if (time < 5 || time > 13) check();
    }
  }
});

test("a relaxed hand has a finger cascade, and the ulnar edge cups towards the thumb", () => {
  for (const side of ["left", "right"] as const) {
    const rig = aliceRig(),
      rest = fingersAt(rig, side, 0),
      open = fingersAt(rig, side, 1),
      grip = fingersAt(rig, side, -1);
    assert.ok(rest.bends.every((v, i, a) => !i || v > a[i - 1] + 3));
    assert.ok(rest.bends[3] - rest.bends[0] > 13);
    assert.ok(
      rest.bends[0] > open.bends[0] + 7 && grip.bends[1] > rest.bends[1] + 30,
    );
    assert.ok(
      grip.thumbDepth > rest.thumbDepth + 0.018 && grip.thumbAcross < -0.012,
    );
    assert.ok(grip.knuckle.clone().sub(open.knuckle).dot(open.normal) > 0.002);
    assert.ok(
      Math.abs(grip.knuckle.length() - open.knuckle.length()) < 0.00001,
    );
  }
});

test("opening starts at the index side; closing starts at the little-finger side", () => {
  const r = aliceRig();
  const rest = fingersAt(r, "left", 0),
    open = fingersAt(r, "left", 1);
  fingersAt(r, "left", 0);
  const opening = fingersAt(r, "left", 1, 0.1);
  const portion = (v: number, start: number, end: number) =>
    (v - start) / (end - start);
  assert.ok(
    portion(opening.bends[0], rest.bends[0], open.bends[0]) >
      portion(opening.bends[3], rest.bends[3], open.bends[3]) + 0.1,
  );
  const grip = fingersAt(r, "left", -1);
  fingersAt(r, "left", 1);
  const closing = fingersAt(r, "left", -1, 0.08);
  assert.ok(
    portion(closing.bends[3], open.bends[3], grip.bends[3]) >
      portion(closing.bends[0], open.bends[0], grip.bends[0]) + 0.1,
  );
});

test("sleeve contact follows the arm that lifts and settles back at the sides", () => {
  const rig = aliceRig();
  assert.ok(rig.contact.update().every((w) => w > 0.999));
  for (let frame = 0; frame < 100; frame++)
    filteredPose(
      rig,
      rig.joints,
      aliceMotion(frame / 30, {
        gesture: "wave",
        gestureAt: 0,
        waveSide: "left",
      }),
      "left",
      1 / 30,
    );
  const [le, lc, re, rc] = rig.contact.update();
  assert.ok(
    lc < 0.05 && le < 0.9 && re > 0.9 && rc > 0.9,
    `${le}, ${lc}, ${re}, ${rc}`,
  );
  for (let frame = 100; frame < 260; frame++)
    filteredPose(rig, rig.joints, aliceMotion(frame / 30), "left", 1 / 30);
  assert.ok(rig.contact.update().every((w) => w > 0.985));
});

test("the sparse uniform fit belongs to the shipped model and its shared vertex layout", () => {
  const bytes = readFileSync(
    new URL("../public/avatars/alice/alice-ready.vrm", import.meta.url),
  );
  assert.equal(
    createHash("sha256").update(bytes).digest("hex"),
    fit.sourceSha256,
  );
  const model = JSON.parse(
    bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString(),
  );
  const body = model.nodes.find((n: { name: string }) => n.name === "Body");
  const position = model.meshes[body.mesh].primitives[0].attributes.POSITION;
  assert.equal(model.accessors[position].count, fit.vertexCount);
  for (const side of ["left", "right"] as const) {
    const seen = new Set<number>();
    for (const [i, x, y, z, share] of fit[side]) {
      assert.ok(
        Number.isInteger(i) && i >= 0 && i < fit.vertexCount && !seen.has(i),
      );
      seen.add(i);
      assert.ok(
        [x, y, z, share].every(Number.isInteger) && share >= 0 && share <= 255,
      );
    }
  }
});
