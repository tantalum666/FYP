import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { Mesh, Scene } from "three";
import { VRMExpressionManager, type VRM } from "@pixiv/three-vrm";
import { FacePerformance } from "../src/companion/face-performance.ts";
import { replyDelivery } from "../src/companion/delivery.ts";
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
