"""Build one panel per face, with integral M3 tabs. Dimensions are millimetres."""
import json
import math
from itertools import combinations
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enclosure_v2 as layout
from build_enclosure_v2 import (
    X, Y, Z, W, D, H, T, N, S, S0, YTOP, Z0, CC, SS,
    ARM_WIRE, BAY_D, OPEN_Z, SCREEN, XL, XR,
    add, box, cut, cyl, cutter_box, dimension_bounds, minus, new_col, poly,
)

OUTPUT = Path(__file__).resolve().parent / 'enclosure_320mm_v3'
SIDE_WALL = 5.0
EDGE_CLEARANCE = 0.2
BED = 320.0
SCREW_RADIUS = 1.7
NUT_FLATS = 5.8
NUT_DEPTH = 2.85
TAB_DEPTH = 7.0


def front_profile():
    """The upper display surround and lower entry lintel share one folded section."""
    return [
        (0, T + EDGE_CLEARANCE),
        (T, T + EDGE_CLEARANCE),
        (T, Z0 + T - T / CC),
        (YTOP, H - T / SS),
        (YTOP, H),
        (0, Z0),
    ]


def clamp_joint(owner, cover, point, axis):
    """Drill the cover and integral tab on one axis and recess a nut from inside."""
    a = Vector(axis)
    center = Vector(point)
    hole_center = center + a * 1.5
    for part in (owner, cover):
        cut(part, cyl(hole_center, a, SCREW_RADIUS, 14, layout.tools))
    u = a.cross(Vector(Z if abs(a.z) < 0.8 else X)).normalized()
    v = a.cross(u).normalized()
    r = NUT_FLATS / (2 * math.cos(math.pi / 6))
    outline = [(r * math.cos(i * math.tau / 6), r * math.sin(i * math.tau / 6)) for i in range(6)]
    cut(owner, poly('Nut pocket cutter', outline, center, u, v, a,
                    TAB_DEPTH - NUT_DEPTH, TAB_DEPTH + 0.5, layout.tools))
    return (owner, cover, center, a)


def side_tabs(side, hand, top, bottom, front, rear):
    if hand == 'Left':
        x0, x1, xc = SIDE_WALL - 0.5, SIDE_WALL + 16, SIDE_WALL + 8.5
    else:
        x0, x1, xc = W - SIDE_WALL - 16, W - SIDE_WALL + 0.5, W - SIDE_WALL - 8.5
    joints = []
    for y in (113, 178):
        cut(side, cutter_box((x0, x1, y - 8, y + 8, H - T - TAB_DEPTH, H - T)), 'UNION')
        joints.append(clamp_joint(side, top, (xc, y, H - T), minus(Z)))
    for y in (41, 145):
        cut(side, cutter_box((x0, x1, y - 8, y + 8, T, T + TAB_DEPTH)), 'UNION')
        joints.append(clamp_joint(side, bottom, (xc, y, T), Z))
    for z in (48, 145):
        cut(side, cutter_box((x0, x1, D - T - TAB_DEPTH, D - T, z - 8, z + 8)), 'UNION')
        joints.append(clamp_joint(side, rear, (xc, D - T, z), minus(Y)))
    cut(side, cutter_box((x0, x1, T, T + TAB_DEPTH, 43, 59)), 'UNION')
    joints.append(clamp_joint(side, front, (xc, T, 51), Y))
    for s in (33, 87):
        cut(side, layout.slant_cut((x0, x1, s - 8, s + 8, T, T + TAB_DEPTH)), 'UNION')
        joints.append(clamp_joint(side, front, add(S0, (X, xc), (S, s), (N, T)), N))
    return joints


def floor_tabs(floor, front, rear):
    joints = []
    for x in (52, W - 52):
        cut(floor, cutter_box((x - 8, x + 8, T, T + TAB_DEPTH, T - 0.5, 19)), 'UNION')
        joints.append(clamp_joint(floor, front, (x, T, 11), Y))
    for x in (76, W - 76):
        cut(floor, cutter_box((x - 8, x + 8, D - T - TAB_DEPTH, D - T, T - 0.5, 19)), 'UNION')
        joints.append(clamp_joint(floor, rear, (x, D - T, 11), minus(Y)))
    return joints


def check_single_solid(obj):
    layout.validate_mesh(obj)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    seen = set()
    pending = [next(iter(mesh.verts))]
    while pending:
        vertex = pending.pop()
        if vertex in seen:
            continue
        seen.add(vertex)
        pending.extend(edge.other_vert(vertex) for edge in vertex.link_edges)
    connected = len(seen) == len(mesh.verts)
    mesh.free()
    if not connected:
        raise ValueError(f'{obj.name} has a detached tab or body')


def check_clashes(parts):
    def copy_for_check(part):
        obj = part.copy()
        obj.data = part.data.copy()
        layout.tools.objects.link(obj)
        return obj

    for a, b in combinations(parts, 2):
        probe = copy_for_check(a)
        cut(probe, copy_for_check(b), 'INTERSECT')
        mesh = bmesh.new()
        mesh.from_mesh(probe.data)
        volume = abs(mesh.calc_volume())
        mesh.free()
        bpy.data.objects.remove(probe, do_unlink=True)
        if volume > 0.05:
            raise ValueError(f'{a.name} overlaps {b.name} by {volume:.2f} mm³')


def footprint(obj, axes):
    dimensions = []
    for axis in map(Vector, axes):
        projections = [vertex.co.dot(axis) for vertex in obj.data.vertices]
        dimensions.append(round(max(projections) - min(projections), 2))
    return dimensions


def recenter(obj):
    low, high = dimension_bounds([obj])
    center = (Vector(low) + Vector(high)) / 2
    obj.data.transform(Matrix.Translation(-center))
    obj.location = center


def build():
    scene, mats = layout.start('FYP V3 · Six faces · 320 x 200 x 200 mm')
    panels = new_col('01 SIX OUTER PANELS — PRINT PARTS')
    dock = new_col('04 DOCK TX CARRIER — prototype')
    layout.tools = new_col('_tools')
    shell = mats['Ivory shell']
    left_edge = SIDE_WALL + EDGE_CLEARANCE
    right_edge = W - left_edge
    sides = {}
    for label, bounds in (('Left', (0, SIDE_WALL)), ('Right', (W - SIDE_WALL, W))):
        sides[label] = poly(f'{label} side — full height', layout.side_shape(0, H),
                            (0, 0, 0), Y, Z, X, *bounds, panels, shell)
    left, right = sides.values()
    top = box('Top — Luwu cable hole and phone Qi',
              (left_edge, right_edge, YTOP + EDGE_CLEARANCE, D - T - EDGE_CLEARANCE, H - T, H), panels, shell)
    bottom = box('Bottom — open Mini approach', (left_edge, right_edge, 0, D, 0, T), panels, shell)
    rear = box('Back — vents and service opening',
               (left_edge, right_edge, D - T, D, T + EDGE_CLEARANCE, H - T - EDGE_CLEARANCE), panels, shell)
    front = poly('Front — screen and bay opening in one piece', front_profile(),
                 (0, 0, 0), Y, Z, X, left_edge, right_edge, panels, shell)
    cut(bottom, cutter_box((XL, XR, -1, BAY_D, -1, T + 1)))
    cut(front, cutter_box((XL, XR, -1, 7, -1, OPEN_Z)))
    cut(front, layout.slant_cut((*SCREEN, -2, 7)))
    cut(top, cyl(ARM_WIRE, Z, 11, 12, layout.tools))
    cut(rear, cutter_box((W - 67, W - 25, D - T - 1, D + 1, 43, 68)))
    layout.vent_cut(rear, 'rear')

    joints = side_tabs(left, 'Left', top, bottom, front, rear)
    joints.extend(side_tabs(right, 'Right', top, bottom, front, rear))
    joints.extend(floor_tabs(bottom, front, rear))
    for z in (123, 131, 139, 147, 155):
        cut(right, cutter_box((W - SIDE_WALL - 1, W + 1, 68, 132, z, z + 3.4)))
    carrier = layout.dock_bracket(bottom, bottom, dock, mats['Fasteners under cover'])

    axes = {
        front: (X, S, N), rear: (X, Z, minus(Y)), left: (Y, Z, X), right: (Y, minus(Z), minus(X)),
        top: (X, minus(Y), minus(Z)), bottom: (X, Y, Z), carrier: (X, Y, Z),
    }
    bpy.context.view_layer.update()
    bounds = dimension_bounds(list(panels.objects))
    assert bounds == [[0, 0, 0], [W, D, H]]
    assert len(panels.objects) == 6 and len(joints) == 22
    for part in axes:
        check_single_solid(part)
    for owner, cover, point, axis in joints:
        for part in (owner, cover):
            assert not part.ray_cast(point - axis * 5, axis, distance=13)[0], part.name
    layout.validate_reservations(list(panels.objects), [], carrier, False)
    check_clashes(axes)

    references, _, _, _ = layout.refs(scene, mats)
    footprints = {}
    for part, directions in axes.items():
        size = footprint(part, directions)
        assert max(size[:2]) + 10 <= BED, (part.name, size)
        part['Proposed print size XYZ (mm)'] = str(size)
        footprints[part.name] = size
    for part in list(axes) + list(references.objects):
        recenter(part)

    bpy.data.collections.remove(layout.tools)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    camera = layout.setup_view(scene)
    scene['Prototype'] = 'Six separate faces with integral M3 tabs. Verify fit and assembly before final printing.'
    scene['Outer envelope (mm)'] = '320 × 200 × 200'
    scene['Fasteners'] = '22 panel joints with Ø3.4 clearances and trial M3 nut pockets; two additional dock carrier fasteners'
    scene['Screen and dock'] = 'V2 reference dimensions: draft 157 × 91 screen window, 150 × 160 × 100 Mini opening, rear coil pair'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.view_layer.update()
    assert dimension_bounds(list(panels.objects)) == bounds
    OUTPUT.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'FYP_enclosure_320x200x200_V3_six_panels.blend'))
    qa = dict(outer_bounds_mm=bounds, shell_parts=6, dock_parts=1, separate_joining_parts=0,
              panel_bolt_positions=len(joints), printable_bounds_mm=footprints,
              checks=['single connected solid per part', 'bolt axis clear', 'V2 opening samples clear',
                      'no positive-volume panel or carrier clash above 0.05 mm³',
                      'proposed footprint plus 5 mm each edge within nominal bed'])
    (OUTPUT / 'qa.json').write_text(json.dumps(qa, indent=2, ensure_ascii=False) + '\n')
    print('QA', json.dumps(qa, ensure_ascii=False))

    if '--' in sys.argv and 'render' in sys.argv[sys.argv.index('--') + 1:]:
        scene.render.filepath = str(OUTPUT / 'six_panels_preview.png')
        bpy.ops.render.render(write_still=True)
        references.hide_render = True
        camera.location = (W + 380, -525, 365)
        camera.rotation_euler = (Vector((W / 2, 92, 111)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = 670
        for part, offset in ((front, (0, -75, 0)), (rear, (0, 85, 15)),
                             (left, (-82, 0, 0)), (right, (82, 0, 0)),
                             (top, (0, 5, 76)), (bottom, (0, 0, -53))):
            part.location += Vector(offset)
        scene.render.filepath = str(OUTPUT / 'six_panels_exploded.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    build()
