// Local, checksum-verified assets; the camera worker never loads a public CDN.
import { createHash } from "node:crypto";
import { cp, mkdir, readFile, copyFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const model = JSON.parse(
  await readFile(resolve(root, "config/models.json"), "utf8"),
).pose_lite;
const source = resolve(root, ".runtime/models", model.filename);
const bytes = await readFile(source);
if (createHash("sha256").update(bytes).digest("hex") !== model.sha256)
  throw new Error(
    "Pose model checksum mismatch; run scripts/fetch_models.py first.",
  );
const dest = resolve(root, "frontend/public/posture-assets");
await mkdir(dest, { recursive: true });
await copyFile(source, resolve(dest, model.filename));
await cp(
  resolve(root, "frontend/node_modules/@mediapipe/tasks-vision/wasm"),
  resolve(dest, "wasm"),
  { recursive: true },
);
await writeFile(
  resolve(dest, "manifest.json"),
  JSON.stringify(
    {
      sdk: "@mediapipe/tasks-vision@1.2.3",
      model_sha256: model.sha256,
      license: model.license,
    },
    null,
    2,
  ),
);
console.log("Local posture assets prepared and model checksum verified.");
