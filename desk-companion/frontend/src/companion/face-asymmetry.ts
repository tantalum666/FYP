import { BufferAttribute, BufferGeometry, SkinnedMesh } from "three";
import type { VRM } from "@pixiv/three-vrm";

const shapes = [
  ["Fcl_BRW_Question_L", "Fcl_BRW_Surprised", -1],
  ["Fcl_BRW_Apology_R", "Fcl_BRW_Sorrow", 1],
  ["Fcl_MTH_Smile_R", "Fcl_MTH_Up", 1],
] as const;
type Attribute = BufferGeometry["attributes"][string];

/** Split the original artist's displacements across the centre of the face.
 * The inner and outer lips use the same mask, so opening the mouth stays sealed at its corners. */
export function addAsymmetricShapes(vrm: Pick<VRM, "scene">) {
  const baked = new Map<BufferGeometry, Record<string, number>>();
  const masked = new Map<Attribute, Map<number, BufferAttribute>>();
  function half(source: Attribute, position: Attribute, side: number) {
    let variants = masked.get(source);
    if (!variants) {
      variants = new Map();
      masked.set(source, variants);
    }
    const existing = variants.get(side);
    if (existing) return existing;
    const result = new BufferAttribute(new Float32Array(source.count * 3), 3);
    for (let i = 0; i < source.count; i++) {
      const x = Math.max(
          0,
          Math.min(1, 0.5 + (side * position.getX(i)) / 0.02),
        ),
        w = x * x * (3 - 2 * x);
      result.setXYZ(
        i,
        source.getX(i) * w,
        source.getY(i) * w,
        source.getZ(i) * w,
      );
    }
    variants.set(side, result);
    return result;
  }
  vrm.scene.traverse((mesh) => {
    if (!(mesh instanceof SkinnedMesh) || !mesh.morphTargetDictionary) return;
    const g = mesh.geometry,
      position = g.getAttribute("position"),
      original = mesh.morphTargetDictionary;
    if (
      !g.morphTargetsRelative ||
      !g.morphAttributes.position ||
      original.Fcl_MTH_Up === undefined ||
      original.Fcl_MTH_Smile_R !== undefined
    )
      return;
    let extra = baked.get(g);
    if (!extra) {
      extra = {};
      baked.set(g, extra);
      const positions = [...g.morphAttributes.position!],
        normals = g.morphAttributes.normal
          ? [...g.morphAttributes.normal]
          : null;
      for (const [name, artist, side] of shapes) {
        const id = original[artist];
        if (id === undefined || !positions[id] || (normals && !normals[id]))
          continue;
        extra[name] = positions.length;
        positions.push(half(positions[id], position, side));
        if (normals) normals.push(half(normals[id], position, side));
      }
      g.morphAttributes.position = positions;
      if (normals) g.morphAttributes.normal = normals;
    }
    const weights = mesh.morphTargetInfluences?.slice() ?? [];
    mesh.updateMorphTargets();
    mesh.morphTargetDictionary = { ...original, ...extra };
    weights.forEach((weight, i) => {
      mesh.morphTargetInfluences![i] = weight;
    });
  });
}
