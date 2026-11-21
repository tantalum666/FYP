"""Offline skinned-surface audit. Run with Blender background Python (mathutils + NumPy)."""

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree


def read_asset(path):
    data = path.read_bytes()
    size = struct.unpack_from("<I", data, 12)[0]
    source = json.loads(data[20 : 20 + size])
    payload = memoryview(data)[28 + size :]
    types = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
    sizes = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}

    def accessor(i):
        item = source["accessors"][i]
        view = source["bufferViews"][item["bufferView"]]
        dtype = np.dtype(types[item["componentType"]])
        width = sizes[item["type"]]
        return np.ndarray(
            (item["count"], width),
            dtype=dtype,
            buffer=payload,
            offset=view.get("byteOffset", 0) + item.get("byteOffset", 0),
            strides=(view.get("byteStride", width * dtype.itemsize), dtype.itemsize),
        )

    return source, accessor


class Surface:
    def __init__(self, triangles, positions, joints, weights, binding, fit=None):
        vertices, remap = np.unique(triangles.ravel(), return_inverse=True)
        self.indices = remap.reshape(-1, 3)
        self.faces = self.indices.tolist()
        self.joints = joints[vertices]
        local = np.column_stack((positions[vertices], np.ones(len(vertices), dtype="f4")))
        self.bound = (
            np.einsum("nkij,nj->nki", binding[self.joints], local) * weights[vertices, :, None]
        )

        self.corrections = []
        for delta in fit or []:
            vector = np.column_stack((delta[vertices], np.zeros(len(vertices), dtype="f4")))
            self.corrections.append(
                np.einsum("nkij,nj->nki", binding[self.joints], vector) * weights[vertices, :, None]
            )

    def pose(self, matrices, contact=None):
        bound = self.bound
        if contact is not None:
            for weight, correction in zip(contact, self.corrections):
                if weight:
                    bound = bound + weight * correction
        points = np.einsum("nkrj,nkj->nr", matrices[self.joints, :3, :], bound)
        return points, points.min(0), points.max(0)


def build_surfaces(source, accessor, uniform=None, digits=False):
    result = {}
    for node in (node for node in source["nodes"] if "mesh" in node):
        mesh = source["meshes"][node["mesh"]]
        skin = source["skins"][node["skin"]]
        attrs = mesh["primitives"][0]["attributes"]
        positions = accessor(attrs["POSITION"])
        weights = accessor(attrs["WEIGHTS_0"])
        joints = np.asarray(skin["joints"])[accessor(attrs["JOINTS_0"])]
        names = np.array([n.get("name", "") for n in source["nodes"]])
        dominant = names[np.take_along_axis(joints, weights.argmax(1)[:, None], axis=1)[:, 0]]
        binding = np.zeros((len(names), 4, 4), dtype="f4")
        binding[skin["joints"]] = (
            accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
        )
        fit = []
        if uniform and node["name"] == "Body":
            assert len(positions) == uniform["vertexCount"]
            for side in ("left", "right"):
                rows = np.asarray(uniform[side])
                indices = rows[:, 0].astype(int)
                delta = rows[:, 1:4] * 0.0001
                t = rows[:, 4, None] / 255
                for part in (t, 1 - t):
                    attr = np.zeros((len(positions), 3), dtype="f4")
                    attr[indices] = delta * part
                    fit.append(attr)
        grouped = {}
        for primitive in mesh["primitives"]:
            material = source["materials"][primitive["material"]]["name"]
            faces = accessor(primitive["indices"]).reshape(-1, 3)

            def add(name, selected):
                if len(selected):
                    grouped.setdefault(name, []).append(selected)

            if "Face_00_SKIN" in material:
                add("face", faces)
            elif "Hair" in material and node["name"] == "Hair":
                add("hair", faces)
            elif "HairBack" in material:
                add("hairBack", faces)
            elif "Body_00_SKIN" in material or "Tops_" in material:
                is_body = "Body_00_SKIN" in material
                tags = np.full(len(dominant), "torso", dtype="<U10")
                for prefix, side in (("J_Bip_L_", "L"), ("J_Bip_R_", "R")):
                    for label, suffixes in (
                        ("hand", ("Hand", "Thumb", "Index", "Middle", "Ring", "Little")),
                        ("sleeve", ("LowerArm",)),
                        ("upper", ("UpperArm", "Shoulder")),
                    ):
                        matches = np.zeros(len(dominant), dtype=bool)
                        for suffix in suffixes:
                            matches |= np.char.startswith(dominant, prefix + suffix)
                        tags[matches] = side + label
                for side in ("L", "R"):
                    if is_body:
                        add(side + "hand", faces[(tags[faces] == side + "hand").sum(1) >= 2])
                        distal = np.array(
                            [
                                n.startswith("J_Bip_" + side + "_")
                                and n[-1:] in ("2", "3")
                                and any(
                                    f in n for f in ("Thumb", "Index", "Middle", "Ring", "Little")
                                )
                                for n in dominant
                            ]
                        )
                        add(side + "tips", faces[distal[faces].sum(1) >= 2])
                        terminal = distal & np.char.endswith(dominant, "3")
                        add(side + "distal", faces[terminal[faces].sum(1) >= 2])
                        if digits:
                            for digit in ("Thumb", "Index", "Middle", "Ring", "Little"):
                                member = np.char.startswith(dominant, "J_Bip_" + side + "_" + digit)
                                free = member & distal
                                add(
                                    side + digit,
                                    faces[(member[faces].sum(1) >= 2) & free[faces].any(1)],
                                )

                    else:
                        covered = (tags == side + "sleeve") | (tags == side + "hand")
                        add(side + "sleeve", faces[covered[faces].sum(1) >= 2])
                if not is_body:
                    add("coat", faces[(tags[faces] == "torso").sum(1) >= 2])
            elif "Accessory_Tie" in material or "Bottoms_" in material:
                add("coat", faces)
        for name, parts in grouped.items():
            result[name] = Surface(
                np.concatenate(parts),
                positions,
                joints,
                weights,
                binding,
                fit if name in ("coat", "Lsleeve", "Rsleeve") else None,
            )
    return result


def pair_list(digits=False):
    pairs = []
    for side, other in (("L", "R"), ("R", "L")):
        for source in (side + "hand", side + "sleeve"):
            for target in ("coat", "face", "hair", "hairBack"):
                pairs.append((source, target))
        pairs.extend(
            [
                (side + "hand", other + "sleeve"),
                (side + "tips", side + "sleeve"),
                (side + "distal", side + "sleeve"),
            ]
        )
    if digits:
        for side in ("L", "R"):
            names = [side + n for n in ("Thumb", "Index", "Middle", "Ring", "Little")]
            pairs.extend((a, b) for i, a in enumerate(names) for b in names[i + 1 :])
    return pairs + [("Lhand", "Rhand"), ("Lsleeve", "Rsleeve")]


def scan(matrices, surfaces, pairs, stride, contact=None):
    hits = {}
    for frame in range(0, len(matrices), stride):
        poses = {
            n: s.pose(matrices[frame], contact[frame] if contact is not None else None)
            for n, s in surfaces.items()
        }
        trees = {}

        def tree(name):
            if name not in trees:
                trees[name] = BVHTree.FromPolygons(
                    poses[name][0].tolist(), surfaces[name].faces, all_triangles=True
                )
            return trees[name]

        for a, b in pairs:
            va, amin, amax = poses[a]
            _, bmin, bmax = poses[b]
            if np.any(amax < bmin) or np.any(bmax < amin):
                continue
            overlap = tree(a).overlap(tree(b))
            if not overlap:
                continue
            key = a + "/" + b
            h = hits.setdefault(
                key, {"frames": 0, "max_pairs": 0, "depth_mm": 0, "worst_frame": frame}
            )
            h["frames"] += 1
            h["max_pairs"] = max(h["max_pairs"], len(overlap))
            # With open clothing or hair cards this is local depth at crossing
            # triangles, not a watertight-volume or cloth-physics model.
            vertices = np.unique(surfaces[a].indices[[i for i, _ in overlap]])
            deepest = 0.0
            for v in va[vertices]:
                pt, normal, _, distance = tree(b).find_nearest(v)
                if pt is not None and sum((v[i] - pt[i]) * normal[i] for i in range(3)) < 0:
                    deepest = max(deepest, distance * 1000)
            if deepest > h["depth_mm"]:
                h.update(depth_mm=round(deepest, 2), worst_frame=frame)
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("samples", type=Path)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--side", choices=["left", "right"])
    parser.add_argument("--names", nargs="+")
    parser.add_argument(
        "--digits",
        action="store_true",
        help="Check free portions of each digit against its neighbors.",
    )
    parser.add_argument("--result", default="surfaces.json")
    options = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    asset = Path(__file__).resolve().parents[2] / "public/avatars/alice/alice-ready.vrm"
    source, accessor = read_asset(asset)
    surfaces = build_surfaces(
        source,
        accessor,
        json.loads((asset.parents[3] / "src/companion/uniform-rest.json").read_text()),
        digits=options.digits,
    )
    output = {
        "stride": options.stride,
        "triangles": {k: len(v.faces) for k, v in surfaces.items()},
        "paths": {},
    }
    for case in json.loads((options.samples / "index.json").read_text()):
        if options.side and case["side"] != options.side:
            continue
        if options.names and case["name"] not in options.names:
            continue
        frames = (
            np.memmap(options.samples / case["file"], dtype="<f4", mode="r")
            .reshape(case["count"], case["nodes"], 4, 4)
            .transpose(0, 1, 3, 2)
        )
        key = case["name"] + "/" + case["side"]
        output["paths"][key] = scan(
            frames, surfaces, pair_list(options.digits), options.stride, case.get("uniformContact")
        )
        (options.samples / options.result).write_text(json.dumps(output, indent=2))
        print(key, flush=True)


if __name__ == "__main__":
    main()
