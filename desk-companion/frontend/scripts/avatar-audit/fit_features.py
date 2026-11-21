"""Bake sparse, bind-space appearance edits for the licensed Alice uniform."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesh import read_asset  # noqa: E402


def smooth(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def bell(x, width):
    return np.exp(-((x / width) ** 2))


def nose_depth(x, y, z):
    front = smooth(-z, 0.046, 0.069)
    tip = bell(x, 0.009) * bell(y - 1.409, 0.006)
    bridge = bell(x, 0.0058) * bell(y - 1.418, 0.014)
    return front * (0.00185 * tip + 0.00085 * bridge)


def chest_depth(x, y, z):
    front = smooth(-z, 0.042, 0.108)
    # The outer panel is already occupied by a returning forearm. Blend the
    # fullness into it before the sleeve reaches the jacket.
    width = 1 - smooth(abs(x), 0.027, 0.075)
    height = smooth(y, 1.068, 1.167) * (1 - smooth(y, 1.183, 1.284))
    curve = 0.72 + 0.28 * bell(abs(x) - 0.039, 0.037)
    return 0.012 * height * width * front * curve


def facial_color(pos, uv):
    x, y, z = pos.T
    u, v = uv.T
    front = smooth(-z, 0.047, 0.067)
    under = bell(x - 0.0006, 0.0090) * bell(y - 1.4056, 0.0030)
    wing = bell(abs(x) - 0.0050, 0.0029) * bell(y - 1.4065, 0.0023)
    side = bell(x - 0.0046, 0.0054) * bell(y - 1.414, 0.011)
    crest = bell(x + 0.0013, 0.0035) * bell(y - 1.4115, 0.0042)
    # The closed lip edge in the supplied face atlas is at v=0.757.
    # Its upper and lower skin vertices part with the model's visemes.
    width = 1 - smooth(abs(u - 0.5), 0.044, 0.069)
    seam = width * bell(v - 0.7566, 0.0044)
    upper = width * bell(v - 0.7480, 0.0100)
    lower = width * bell(v - 0.7640, 0.0095)
    colors = np.ones_like(pos)
    for field, rgb in [
        (under, (-0.12, -0.23, -0.25)),
        (wing, (-0.046, -0.10, -0.11)),
        (side, (-0.045, -0.10, -0.105)),
        (crest, (0.038, 0.019, 0.006)),
        (seam, (-0.24, -0.51, -0.44)),
        (upper, (-0.043, -0.21, -0.15)),
        (lower, (-0.018, -0.13, -0.10)),
    ]:
        colors += (field * front)[:, None] * rgb
    return np.clip(colors, 0.30, 1.06)


def profile(accessor, mesh, members, depth, color=None):
    primitives = [pr for pr in mesh["primitives"] if pr["material"] in members]
    ids = np.unique(np.concatenate([accessor(pr["indices"]).ravel() for pr in primitives]))
    attrs = primitives[0]["attributes"]
    positions, normals = accessor(attrs["POSITION"]), accessor(attrs["NORMAL"])
    xyz, original = positions[ids].astype(float), normals[ids].astype(float)
    delta = depth(*xyz.T)
    h = 0.0001
    derivatives = []
    for axis in np.eye(3):
        derivatives.append((depth(*(xyz + h * axis).T) - depth(*(xyz - h * axis).T)) / (2 * h))
    # Inverse transpose of (x,y,z) -> (x,y,z-depth). Preserve the artist's
    # smooth split normals and the material seams instead of welding the face.
    nz = original[:, 2] / (1 - derivatives[2])
    adjusted = np.column_stack(
        (original[:, 0] + derivatives[0] * nz, original[:, 1] + derivatives[1] * nz, nz)
    )
    adjusted /= np.maximum(1e-12, np.linalg.norm(adjusted, axis=1))[:, None]
    edits = np.column_stack(
        (np.rint(delta * 100000), np.rint((adjusted - original) * 10000))
    ).astype(int)
    selected = (np.abs(edits).max(1) > 2) | (edits[:, 0] != 0)
    result = {
        "vertexCount": len(positions),
        "shape": np.column_stack((ids[selected], edits[selected])).tolist(),
    }
    if color:
        colors = np.rint((color(xyz, accessor(attrs["TEXCOORD_0"])[ids]) - 1) * 1000).astype(int)
        active = np.abs(colors).max(1) > 2
        result["tint"] = np.column_stack((ids[active], colors[active])).tolist()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    front = Path(__file__).resolve().parents[2]
    model = front / "public/avatars/alice/alice-ready.vrm"
    source, accessor = read_asset(model)
    meshes = {n["name"]: source["meshes"][n["mesh"]] for n in source["nodes"] if "mesh" in n}
    materials = [m["name"] for m in source["materials"]]
    face = [i for i, m in enumerate(materials) if "Face_00_SKIN" in m]
    body = [
        i
        for i, m in enumerate(materials)
        if "Body_00_SKIN" in m or "_Tops_" in m or "Accessory_Tie" in m
    ]
    assert face and len(body) >= 3
    result = {
        "sourceSha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "face": profile(accessor, meshes["Face"], face, nose_depth, facial_color),
        "body": profile(accessor, meshes["Body"], body, chest_depth),
    }
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
