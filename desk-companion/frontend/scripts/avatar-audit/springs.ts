/** Replay body samples through the shipped VRM0 hair and garment spring solver. */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { Matrix4, Object3D } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import {
  VRMSpringBoneLoaderPlugin,
  type VRMSpringBoneManager,
} from "@pixiv/three-vrm";
import { fitAliceSleeves } from "../../src/companion/sleeve-colliders.ts";
const [input, output] = process.argv.slice(2);
if (!input || !output)
  throw new Error("Pass input and output sample directories");
const source = readFileSync(
  new URL("../../public/avatars/alice/alice-ready.vrm", import.meta.url),
);
const gltf = JSON.parse(
  source.subarray(20, 20 + source.readUInt32LE(12)).toString(),
);
const nodes = gltf.nodes.map(
  ({
    mesh,
    skin,
    ...node
  }: {
    mesh?: number;
    skin?: number;
    [key: string]: unknown;
  }) => node,
);
const skeleton = {
  asset: gltf.asset,
  scene: gltf.scene,
  scenes: gltf.scenes,
  nodes,
  extensionsUsed: ["VRM"],
  extensions: { VRM: gltf.extensions.VRM },
};
const loader = new GLTFLoader();
loader.register((parser) => new VRMSpringBoneLoaderPlugin(parser));
const loaded = await loader.parseAsync(JSON.stringify(skeleton), "");
const springs = loaded.userData.vrmSpringBoneManager as VRMSpringBoneManager;
if (!springs?.joints.size)
  throw new Error("The avatar spring rig was not loaded");
const updateSleeves=process.argv.includes("--fit-sleeves")? fitAliceSleeves(springs):undefined;
const raw = (await Promise.all(
  nodes.map((_: unknown, i: number) => loaded.parser.getDependency("node", i)),
)) as Object3D[];
const parent = new Map(raw.map((node, i) => [node, i]));
const human = new Set<number>(
  gltf.extensions.VRM.humanoid.humanBones.map((b: { node: number }) => b.node),
);
const local = new Matrix4(),
  inverse = new Matrix4(),
  stride = 16 * nodes.length;
mkdirSync(output, { recursive: true });
const cases = JSON.parse(readFileSync(join(input, "index.json"), "utf8"));
const original = raw.map((n) => ({
  p: n.position.clone(),
  q: n.quaternion.clone(),
  s: n.scale.clone(),
}));
for (const c of cases) {
  const buf = readFileSync(join(input, c.file)),
    frames = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const out = new Float32Array(frames.length);
  raw.forEach((n, i) => {
    n.position.copy(original[i].p);
    n.quaternion.copy(original[i].q);
    n.scale.copy(original[i].s);
  });
  for (let f = 0; f < c.count; f++) {
    const offset = f * stride;
    for (let i = 0; i < raw.length; i++) {
      if (f !== 0 && !human.has(i)) continue;
      const node = raw[i],
        p = node.parent ? parent.get(node.parent) : undefined;
      local.fromArray(frames, offset + 16 * i);
      if (p !== undefined)
        local.premultiply(inverse.fromArray(frames, offset + 16 * p).invert());
      local.decompose(node.position, node.quaternion, node.scale);
    }
    loaded.scene.updateMatrixWorld(true);
    if (f === 0) {
      springs.setInitState();
      springs.reset();
    }
    if(c.uniformContact)updateSleeves?.(c.uniformContact[f]);
    springs.update(1 / 30);
    loaded.scene.updateMatrixWorld(true);
    raw.forEach((n, i) => out.set(n.matrixWorld.elements, offset + i * 16));
  }
  writeFileSync(join(output, c.file), new Uint8Array(out.buffer));
}
writeFileSync(join(output, "index.json"), JSON.stringify(cases));
console.log(
  cases.length,
  "paths,",
  springs.joints.size,
  "simulated spring joints",
);
