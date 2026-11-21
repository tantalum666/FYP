"""Bake the uniform's four low-arm contact shapes from a settled resident-rig sample.

blender -b --python scripts/avatar-audit/fit_uniform.py -- /tmp/alice-body /tmp/uniform-rest.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesh import read_asset  # noqa: E402


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def soft_edge(value):
    return 0.004 * np.logaddexp(0, value / 0.004)


def garment(source, accessor, matrices):
    node = next(n for n in source["nodes"] if n.get("name") == "Body")
    mesh = source["meshes"][node["mesh"]]
    skin = source["skins"][node["skin"]]
    attributes = mesh["primitives"][0]["attributes"]
    xyz = accessor(attributes["POSITION"])
    weights = accessor(attributes["WEIGHTS_0"])
    joints = np.asarray(skin["joints"])[accessor(attributes["JOINTS_0"])]
    inverse = np.zeros((len(source["nodes"]), 4, 4))
    inverse[skin["joints"]] = (
        accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    )
    blend = np.einsum("vk,vkij->vij", weights, (matrices @ inverse)[joints])
    world = np.einsum("vij,vj->vi", blend, np.column_stack((xyz, np.ones(len(xyz)))))[:, :3]
    top = np.zeros(len(xyz), dtype=bool)
    skirt = top.copy()
    skirt_faces = []
    for primitive in mesh["primitives"]:
        material = source["materials"][primitive["material"]]["name"]
        vertices = accessor(primitive["indices"]).ravel()
        if "Tops_" in material:
            top[vertices] = True
        elif "Bottoms_" in material:
            skirt[vertices] = True
            skirt_faces.append(vertices.reshape(-1, 3))
    return world, blend, joints, weights, top, skirt, np.concatenate(skirt_faces)


def fit_side(
    side, sign, bone_names, matrices, world, blend, joints, weights, top, skirt, skirt_faces
):
    prefix = "J_Bip_" + side + "_"
    by_name = {name: i for i, name in enumerate(bone_names)}
    upper, elbow, wrist, finger = (
        matrices[by_name[prefix + name], :3, 3]
        for name in ("UpperArm", "LowerArm", "Hand", "Middle3")
    )
    y, z = world[:, 1], world[:, 2]
    x = sign * world[:, 0]
    heights = [finger[1], wrist[1], elbow[1], upper[1]]
    center_x = np.interp(y, heights, [sign * pt[0] for pt in (finger, wrist, elbow, upper)])
    center_z = np.interp(y, heights, [pt[2] for pt in (finger, wrist, elbow, upper)])
    inner_radius = np.interp(
        y,
        [finger[1], wrist[1] - 0.018, wrist[1] + 0.025, elbow[1], upper[1]],
        [0.038, 0.041, 0.038, 0.032, 0.029],
    )
    # Separate only fabric along the resting arm. Front panels, the neckline
    # and the other side of the garment retain their original shape.
    boundary = center_x - inner_radius
    zone = (
        smooth((y - finger[1] + 0.14) / 0.05)
        * smooth((upper[1] - 0.016 - y) / 0.094)
        * smooth((0.147 - np.abs(z - center_z)) / 0.058)
    )
    limb = np.zeros(len(world))
    for k in range(4):
        names = bone_names[joints[:, k]]
        is_arm = np.zeros(len(world), dtype=bool)
        for joint in ("UpperArm", "LowerArm", "Hand", "Thumb", "Index", "Little", "Middle", "Ring"):
            is_arm |= np.char.startswith(names, prefix + joint)
        limb += weights[:, k] * is_arm
    sleeve = smooth((limb - 0.10) / 0.80)
    jacket_in = soft_edge(
        x - (boundary - 0.004 - 0.010 * skirt * smooth((wrist[1] + 0.02 - y) / 0.060))
    )
    sleeve_out = soft_edge(boundary + 0.004 - x)
    shift = zone * (top * sleeve * sleeve_out - (skirt + top * (1 - sleeve)) * jacket_in)
    shift = np.where(skirt, np.clip(shift, -0.008, 0.008), shift)
    # The inner cuff can meet the pleat below the jacket. Let this side
    # of the cuff yield to the actual skirt surface, preserving the hem.
    dressed = world.copy()
    dressed[:, 0] += sign * shift
    pleats = BVHTree.FromPolygons(dressed.tolist(), skirt_faces.tolist(), all_triangles=True)
    for i in np.flatnonzero(top & (sleeve > 0.7) & (x > 0.072) & (y < wrist[1] + 0.11)):
        outer = x[i] + shift[i]
        for dy, dz in ((0, 0), (-0.014, 0), (0.014, 0), (0, -0.014), (0, 0.014)):
            hit = pleats.ray_cast((sign * 0.55, y[i] + dy, z[i] + dz), (-sign, 0, 0), 0.45)[0]
            if hit is not None:
                margin = 0.006 if (dy, dz) == (0, 0) else 0.004
                outer = max(outer, sign * hit[0] + margin)
        shift[i] = outer - x[i]
    ids = np.flatnonzero((top | skirt) & (x > 0.072) & (np.abs(shift) > 0.00020))
    delta = np.zeros((len(ids), 3))
    delta[:, 0] = sign * shift[ids]
    local = np.linalg.solve(blend[ids, :3, :3], delta[..., None])[:, :, 0]
    elbow_mix = np.rint(255 * smooth((y[ids] - wrist[1] + 0.005) / (elbow[1] - wrist[1] + 0.01)))
    # Rows are shared POSITION indices, bind-space offsets in 0.1 mm, and the
    # elbow's share of each offset. The cuff controls the remainder.
    return np.column_stack((ids, np.rint(local * 10000), elbow_mix)).astype(int).tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("samples", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    model = Path(__file__).resolve().parents[2] / "public/avatars/alice/alice-ready.vrm"
    source, accessor = read_asset(model)
    cases = json.loads((args.samples / "index.json").read_text())
    case = next(c for c in cases if c["name"] == "idle" and c["side"] == "left")
    raw = np.memmap(args.samples / case["file"], dtype="<f4", mode="r")
    matrices = raw.reshape(case["count"], case["nodes"], 4, 4)[90].transpose(0, 2, 1)
    data = garment(source, accessor, matrices)
    names = np.array([n.get("name", "") for n in source["nodes"]])
    result = {
        "vertexCount": len(data[0]),
        "sourceSha256": hashlib.sha256(model.read_bytes()).hexdigest(),
    }
    for name, side, sign in (("left", "L", 1), ("right", "R", -1)):
        result[name] = fit_side(side, sign, names, matrices, *data)
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
