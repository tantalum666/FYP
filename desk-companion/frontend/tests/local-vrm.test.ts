import test from "node:test";
import assert from "node:assert/strict";
import { validateLocalVrm } from "../src/companion/local-vrm.ts";

function glb(data: unknown): ArrayBuffer {
  const text = new TextEncoder().encode(JSON.stringify(data));
  const length = Math.ceil(text.length / 4) * 4;
  const bytes = new ArrayBuffer(20 + length);
  const view = new DataView(bytes);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, bytes.byteLength, true);
  view.setUint32(12, length, true);
  view.setUint32(16, 0x4e4f534a, true);
  new Uint8Array(bytes, 20).fill(32);
  new Uint8Array(bytes, 20).set(text);
  return bytes;
}

test("local avatar supports both VRM generations with embedded resources", () => {
  for (const extension of ["VRM", "VRMC_vrm"])
    assert.doesNotThrow(() =>
      validateLocalVrm(
        glb({
          extensions: { [extension]: {} },
          buffers: [{ byteLength: 0 }],
          images: [{ bufferView: 0 }],
        }),
      ),
    );
});

test("local avatar cannot request a remote buffer or texture", () => {
  for (const resource of ["images", "buffers"])
    assert.throws(
      () =>
        validateLocalVrm(
          glb({
            extensions: { VRM: {} },
            [resource]: [{ uri: "https://example.invalid/track" }],
          }),
        ),
      /VRM_EXTERNAL_RESOURCE/,
    );
});

test("renaming an ordinary GLB or truncated file does not make it a VRM", () => {
  assert.throws(
    () => validateLocalVrm(glb({ asset: { version: "2.0" } })),
    /VRM_EXTENSION/,
  );
  const valid = glb({ extensions: { VRM: {} } });
  assert.throws(
    () => validateLocalVrm(valid.slice(0, valid.byteLength - 1)),
    /VRM_FORMAT/,
  );
  assert.throws(() => validateLocalVrm(new ArrayBuffer(16)), /VRM_SIZE/);
});
