import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  BufferGeometry,
  Float32BufferAttribute,
  Mesh,
  Scene,
  SkinnedMesh,
} from "three";
import { MotionCues } from "../src/companion/motion-cues.ts";
import { conversationalFace } from "../src/companion/facial-cues.ts";
import { addAsymmetricShapes } from "../src/companion/face-asymmetry.ts";
import { VRMExpressionManager, type VRM } from "@pixiv/three-vrm";
import { FacePerformance } from "../src/companion/face-performance.ts";
import { replyDelivery, SpokenDelivery } from "../src/companion/delivery.ts";
import {
  showDelivery,
  subscribeDelivery,
} from "../src/companion/interaction.ts";

test("native face shapes distinguish caring from joy and leave room for speech", () => {
  const bytes = readFileSync(
    new URL("../public/avatars/alice/alice-ready.vrm", import.meta.url),
  );
  const gltf = JSON.parse(
    bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString(),
  );
  const names: string[] = gltf.meshes.find(
    (m: { extras?: { targetNames?: string[] } }) =>
      m.extras?.targetNames?.includes("Fcl_BRW_Sorrow"),
  ).extras.targetNames;
  const mesh = new Mesh();
  mesh.morphTargetDictionary = Object.fromEntries(names.map((n, i) => [n, i]));
  mesh.morphTargetInfluences = names.map(() => 0);
  const manager = new VRMExpressionManager(),
    scene = new Scene();
  scene.add(mesh);
  const face = new FacePerformance({
    scene,
    expressionManager: manager,
  } as VRM);
  const value = (key: string) =>
    mesh.morphTargetInfluences![names.indexOf("Fcl_" + key)];
  function apply(mood: "comfort" | "celebrate", loudness: number) {
    manager.resetValues();
    face.apply(manager, { face: mood, weight: 1, wink: 0 }, loudness, 1);
    manager.update();
  }
  apply("comfort", 0);
  assert.ok(value("BRW_Sorrow") > 0.85 && value("EYE_Sorrow") > 0.6);
  assert.equal(value("EYE_Joy"), 0);
  apply("celebrate", 0);
  const lips = value("MTH_Joy");
  assert.ok(
    lips > 0.8 && value("EYE_Joy") > 0.7 && value("BRW_Sorrow") < 0.005,
  );
  apply("celebrate", 1);
  assert.ok(value("MTH_Joy") < lips * 0.2 && value("EYE_Joy") > 0.7);
});

test("explicit neutral overrides text and a late viewer never replays a private turn", () => {
  assert.equal(
    replyDelivery("neutral", "Congratulations on the sale"),
    "neutral",
  );
  assert.equal(
    replyDelivery(undefined, "OK, the order is confirmed."),
    "neutral",
  );
  assert.equal(replyDelivery(undefined, "唔使客氣，我喺度。"), "appreciate");
  const got: string[] = [];
  showDelivery("comfort");
  const stop = subscribeDelivery((v) => got.push(v));
  assert.deepEqual(got, []);
  showDelivery("celebrate");
  stop();
  showDelivery("curious");
  assert.deepEqual(got, ["celebrate"]);
});

test("a split Live caption reacts once and a late packet cannot start an old reaction again", () => {
  const scene = new SpokenDelivery();
  assert.equal(
    scene.receive({ role: "user", text: "恭喜你", caption_group: 2 }),
    null,
  );
  assert.equal(
    scene.receive({ role: "assistant", text: "恭", caption_group: 2 }),
    null,
  );
  assert.equal(
    scene.receive({ role: "assistant", text: "喜！", caption_group: 2 }),
    "celebrate",
  );
  assert.equal(
    scene.receive({ role: "assistant", text: "恭喜", caption_group: 2 }),
    null,
  );
  scene.finish();
  assert.equal(
    scene.receive({ role: "assistant", text: "恭喜", caption_group: 2 }),
    null,
  );
  assert.equal(
    scene.receive({
      role: "assistant",
      text: "I'm so sorry to hear that.",
      caption_group: 3,
    }),
    "comfort",
  );
});

test("a social delivery stays with the gesture and yields to the next reply", () => {
  const cues = new MotionCues();
  for (const [tone, gesture] of [
    ["relieved", "relax"],
    ["bashful", "hairTuck"],
    ["apologetic", "nod"],
  ] as const) {
    cues.respond(1, tone);
    const cue = cues.sample(1.3, "idle");
    assert.equal(cue?.gesture, gesture);
    assert.equal(cue.delivery, tone);
    assert.equal(
      conversationalFace("idle", gesture, 0.8, 1, cue.delivery, null)?.face,
      tone,
    );
  }
  cues.respond(2, "neutral");
  assert.equal(cues.sample(2.1, "idle"), null);
  assert.equal(
    conversationalFace("listening", null, 0, 0, undefined, null)?.face,
    "attentive",
  );
  assert.equal(
    conversationalFace("thinking", null, 0, 0, undefined, null)?.face,
    "pensive",
  );
  assert.equal(conversationalFace("idle", null, 0, 0, undefined, null), null);
  const exhale = conversationalFace("idle", "relax", 0.9, 1, "relieved", null)!;
  const recover = conversationalFace(
    "idle",
    "relax",
    2.8,
    1,
    "relieved",
    null,
  )!;
  assert.ok((exhale.eyelids ?? 0) > 0.45 && recover.eyelids === 0);
  assert.equal(exhale.mouthFace, "relieved");
  assert.equal(recover.mouthFace, "appreciate");
});

test("one-sided corrections preserve the existing visemes and leave a silent mouth at rest", () => {
  const g = new BufferGeometry();
  g.setAttribute(
    "position",
    new Float32BufferAttribute([-0.02, 0, 0, 0, 0, 0, 0.02, 0, 0], 3),
  );
  const targets = [
    "Fcl_MTH_Up",
    "Fcl_BRW_Surprised",
    "Fcl_BRW_Sorrow",
    "Fcl_MTH_Close",
    "Fcl_MTH_A",
  ];
  g.morphTargetsRelative = true;
  g.morphAttributes.position = targets.map((name) => {
    const attr = new Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0], 3);
    attr.name = name;
    return attr;
  });
  const scene = new Scene(),
    mesh = new SkinnedMesh(g),
    shared = new SkinnedMesh(g);
  scene.add(mesh, shared);
  mesh.morphTargetInfluences![4] = 0.33;
  addAsymmetricShapes({ scene });
  const ids = mesh.morphTargetDictionary!;
  assert.deepEqual(
    targets.map((n) => ids[n]),
    [0, 1, 2, 3, 4],
  );
  assert.deepEqual(shared.morphTargetDictionary, ids);
  assert.equal(mesh.morphTargetInfluences![4], 0.33);
  const smile = g.morphAttributes.position![ids.Fcl_MTH_Smile_R],
    brow = g.morphAttributes.position![ids.Fcl_BRW_Question_L];
  assert.deepEqual(
    [0, 1, 2].map((i) => smile.getY(i)),
    [0, 0.5, 1],
  );
  assert.deepEqual(
    [0, 1, 2].map((i) => brow.getY(i)),
    [1, 0.5, 0],
  );
  addAsymmetricShapes({ scene });
  assert.equal(g.morphAttributes.position!.length, 8);
  const manager = new VRMExpressionManager(),
    face = new FacePerformance({ scene, expressionManager: manager } as VRM);
  face.apply(manager, null, 0, 1);
  manager.update();
  assert.ok(mesh.morphTargetInfluences![ids.Fcl_MTH_Close] > 0.9);
  manager.resetValues();
  face.apply(manager, null, 0.3, 1 / 30);
  manager.update();
  assert.equal(mesh.morphTargetInfluences![ids.Fcl_MTH_Close], 0);
});

test("the localized fit uses the licensed mesh and keeps normalized color on facial skin", () => {
  const model = readFileSync(
    new URL("../public/avatars/alice/alice-ready.vrm", import.meta.url),
  );
  const patch = JSON.parse(
    readFileSync(
      new URL("../src/companion/alice-surface.json", import.meta.url),
      "utf8",
    ),
  );
  assert.equal(
    createHash("sha256").update(model).digest("hex"),
    patch.sourceSha256,
  );
  for (const part of [patch.face, patch.body]) {
    const seen = new Set<number>();
    for (const [i, depth, ...normal] of part.shape) {
      assert.ok(i >= 0 && i < part.vertexCount && !seen.has(i));
      seen.add(i);
      assert.ok(
        Number.isInteger(depth) &&
          depth >= 0 &&
          depth <= 1200 &&
          normal.length === 3,
      );
    }
  }
  assert.ok(
    patch.face.tint.every(
      ([i, ...tint]: number[]) =>
        i < patch.face.vertexCount &&
        tint.length === 3 &&
        tint.every((c) => c >= -700 && c <= 60),
    ),
  );
});
