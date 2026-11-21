import { BufferAttribute, BufferGeometry, SkinnedMesh } from "three";
import { MToonMaterial, type VRM } from "@pixiv/three-vrm";
import detail from "./alice-surface.json" with { type: "json" };

type Patch = typeof detail.body;
type Attribute = BufferGeometry["attributes"][string];

/** Apply the baked changes once in bind space. The original skinning,
 * visemes, cloth correctives, texture and their vertex indices stay in use. */
export function applyAliceSurface(vrm: Pick<VRM, "scene">) {
  const geometrySeen = new Set<BufferGeometry>();
  const positions = new Map<Attribute, Attribute>();
  const normals = new Map<Attribute, Attribute>();
  let tint: BufferAttribute | undefined;
  function shape(geometry: BufferGeometry, patch: Patch) {
    if (geometrySeen.has(geometry)) return;
    geometrySeen.add(geometry);
    const position = geometry.getAttribute("position");
    const normal = geometry.getAttribute("normal");
    let shaped = positions.get(position),
      shaded = normals.get(normal);
    if (!shaped) {
      shaped = position.clone();
      for (const [i, depth] of patch.shape)
        shaped.setZ(i, position.getZ(i) - depth / 100000);
      positions.set(position, shaped);
    }
    if (normal && !shaded) {
      shaded = normal.clone();
      for (const [i, , x, y, z] of patch.shape)
        shaded.setXYZ(
          i,
          normal.getX(i) + x / 10000,
          normal.getY(i) + y / 10000,
          normal.getZ(i) + z / 10000,
        );
      normals.set(normal, shaded);
    }
    geometry.setAttribute("position", shaped);
    if (shaded) geometry.setAttribute("normal", shaded);
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
  }
  vrm.scene.traverse((node) => {
    if (!(node instanceof SkinnedMesh)) return;
    const materials = Array.isArray(node.material)
      ? node.material
      : [node.material];
    const geometry = node.geometry;
    const face = materials.some((m) => m.name.includes("Face_00_SKIN"));
    const body = materials.some((m) =>
      /Body_00_SKIN|_Tops_|Accessory_Tie/.test(m.name),
    );
    if (!face && !body) return;
    const patch = face ? detail.face : detail.body;
    if (geometry.getAttribute("position")?.count !== patch.vertexCount) return;
    shape(geometry, patch);
    if (!face) return;
    if (!tint) {
      tint = new BufferAttribute(
        new Float32Array(patch.vertexCount * 3).fill(1),
        3,
      );
      for (const [i, r, g, b] of detail.face.tint)
        tint.setXYZ(i, 1 + r / 1000, 1 + g / 1000, 1 + b / 1000);
    }
    geometry.setAttribute("color", tint);
    for (const material of materials)
      if (material instanceof MToonMaterial) {
        // MToon 3.5 multiplies RGB factors by vColor; Three r186 supplies RGBA.
        // The RGB swizzle is also valid with the older three-component varying.
        material.fragmentShader = material.fragmentShader.replace(
          /(diffuseColor\.rgb|material\.shadeColor\.rgb) \*= vColor;/g,
          "$1 *= vColor.rgb;",
        );
        material.ignoreVertexColor = false;
        material.vertexColors = true;
        material.needsUpdate = true;
      }
  });
}
