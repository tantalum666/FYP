import {
  VRMSpringBoneColliderShapeSphere,
  type VRMSpringBoneManager,
} from "@pixiv/three-vrm";

/** Alice's uniform is wider than the bare-arm spheres shipped with the VRM. */
export function fitAliceSleeves(
  manager: VRMSpringBoneManager | null | undefined,
) {
  if (!manager) return;
  const sleeves = manager.colliderGroups.filter((group) =>
    group.colliders.some((c) =>
      /^J_Bip_[LR]_(UpperArm|LowerArm|Hand)$/.test(c.parent?.name ?? ""),
    ),
  );
  for (const group of sleeves)
    for (const collider of group.colliders) {
      const shape = collider.shape;
      if (!(shape instanceof VRMSpringBoneColliderShapeSphere)) continue;
      const name = collider.parent?.name ?? "";
      const radius = name.endsWith("UpperArm")
        ? 0.092
        : name.endsWith("LowerArm")
          ? 0.101 + Math.min(0.017, shape.offset.length() * 0.12)
          : 0.102;
      shape.radius = Math.max(shape.radius, radius);
    }
  // The coat hem already has springs. Let their existing solver see the same
  // two sleeves as the hair does, including during a forward bow.
  for (const joint of manager.joints) {
    if (!joint.bone.name.includes("CoatSkirt")) continue;
    joint.colliderGroups = [...new Set([...joint.colliderGroups, ...sleeves])];
  }
}
